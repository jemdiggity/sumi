use crate::{
    process::{self, OwnedChild},
    store::{self, Definition, Lock, Run, Store},
    Action,
};
use anyhow::{bail, Context, Result};
use chrono::{DateTime, SecondsFormat};
use serde::Serialize;
use serde_json::json;
use std::{
    fs::{self, File},
    io::{self, Write},
    os::unix::process::CommandExt,
    path::PathBuf,
    process::{Command, Stdio},
    sync::{
        atomic::{AtomicBool, Ordering},
        Arc,
    },
    thread,
    time::Duration,
};

pub struct Scheduler {
    root: PathBuf,
    store: Store,
    stopped: Arc<AtomicBool>,
}
impl Scheduler {
    pub fn new(root: PathBuf, stopped: Arc<AtomicBool>) -> Self {
        Self {
            store: Store::new(&root),
            root,
            stopped,
        }
    }
    fn lock(&self, name: &str, blocking: bool) -> Result<Lock> {
        Lock::acquire(&self.store.runtime.join(name), blocking, &self.stopped)?
            .with_context(|| format!("Scheduler is busy ({name})"))
    }
    fn reconcile(&self) -> Result<()> {
        for mut run in self.store.records()? {
            if !run.active() {
                continue;
            }
            if run.pgid.is_none() || process::group_alive(run.pgid.unwrap())? {
                bail!("Run {} needs recovery: process ownership is uncertain or group {:?} still exists. Inspect {}. Stop surviving processes; if pgid is null, verify the command is stopped before manually marking run.json interrupted with an ended timestamp. No new run was launched.", run.run_id, run.pgid, self.store.runtime.join(&run.run_id).display());
            }
            run.state = "interrupted".into();
            run.ended = Some(store::now());
            run.exit_code = None;
            run.error = Some("Launcher exited before recording completion".into());
            self.store.save_run(&run)?;
        }
        Ok(())
    }
    fn edit(&self, action: Action) -> Result<()> {
        let _guard = self.lock("config.lock", true)?;
        let mut items = self.store.load()?;
        let result = match action {
            Action::Add { id, every, command } => {
                if !store::valid_id(&id) {
                    bail!("Invalid schedule ID: use 1–64 letters, digits, underscores or hyphens, beginning with a letter or digit");
                }
                store::interval(&every)?;
                if command.is_empty()
                    || command[0].is_empty()
                    || command.iter().any(|s| s.contains('\0'))
                {
                    bail!("Provide a command after --");
                }
                if items.iter().any(|i| i.id == id) {
                    bail!("Schedule already exists: {id}");
                }
                let item = Definition {
                    id,
                    every,
                    command,
                    generation: store::uuid(),
                    enabled: true,
                    anchor: store::now(),
                    extra: Default::default(),
                };
                items.push(item.clone());
                item
            }
            Action::Pause { ref id } | Action::Resume { ref id } | Action::Remove { ref id } => {
                let index = items
                    .iter()
                    .position(|i| i.id == *id)
                    .with_context(|| format!("Unknown schedule: {id}"))?;
                if matches!(action, Action::Remove { .. }) {
                    if self
                        .store
                        .records()?
                        .iter()
                        .any(|r| r.generation == items[index].generation && r.active())
                    {
                        bail!("Cannot remove a running or unreconciled schedule; run serve to reconcile it first");
                    }
                    items.remove(index)
                } else {
                    let item = &mut items[index];
                    item.enabled = matches!(action, Action::Resume { .. });
                    if item.enabled {
                        item.anchor = store::now();
                    }
                    item.clone()
                }
            }
            _ => unreachable!(),
        };
        store::atomic(&self.store.definitions, &items)?;
        print_json(&result)
    }
    fn listing(&self) -> Result<()> {
        let _guard = self.lock("config.lock", true)?;
        let records = self.store.records()?;
        let mut values = vec![];
        for item in self.store.load()? {
            let latest = latest(&item, &records);
            let next = if item.enabled {
                Some(
                    DateTime::from_timestamp_micros((due_at(&item, &records)? * 1e6) as i64)
                        .context("Schedule timestamp is out of range")?
                        .to_rfc3339_opts(SecondsFormat::Micros, false),
                )
            } else {
                None
            };
            values.push(json!({"id":item.id,"enabled":item.enabled,"every":item.every,"command":item.command,
                "next_due":next,"running":latest.is_some_and(|r| r.active()),"last_result":latest}));
        }
        print_json(&values)
    }
    // Execution guard is shared with Python and held through recovery, spawn and cleanup.
    fn run(&self, name: Option<&str>, wait_if_busy: bool) -> Result<Option<Run>> {
        let Some(_execution) = Lock::acquire(
            &self.store.runtime.join("execution.lock"),
            false,
            &self.stopped,
        )?
        else {
            if wait_if_busy {
                return Ok(None);
            }
            bail!("Scheduler is busy (execution.lock)");
        };
        self.reconcile()?;
        let config = self.lock("config.lock", true)?;
        let items = self.store.load()?;
        let records = self.store.records()?;
        let item = if let Some(name) = name {
            items
                .iter()
                .find(|i| i.id == name)
                .with_context(|| format!("Unknown schedule: {name}"))?
        } else {
            let mut due = vec![];
            for i in &items {
                let when = due_at(i, &records)?;
                if i.enabled && when <= store::now() {
                    due.push((when, i));
                }
            }
            due.sort_by(|a, b| a.0.total_cmp(&b.0).then_with(|| a.1.id.cmp(&b.1.id)));
            let Some((_, item)) = due.first() else {
                return Ok(None);
            };
            *item
        };
        if self.stopped.load(Ordering::Relaxed) {
            bail!("Interrupted");
        }
        let run_id = store::uuid();
        let directory = self.store.runtime.join(&run_id);
        fs::create_dir_all(&directory)?;
        let mut record = Run {
            run_id,
            schedule_id: item.id.clone(),
            generation: item.generation.clone(),
            command: item.command.clone(),
            project: self.root.to_string_lossy().into_owned(),
            started: store::now(),
            ended: None,
            state: "starting".into(),
            exit_code: None,
            pgid: None,
            stdout: directory.join("stdout.log").to_string_lossy().into_owned(),
            stderr: directory.join("stderr.log").to_string_lossy().into_owned(),
            error: None,
            extra: Default::default(),
        };
        self.store.save_run(&record)?;
        let spawn = (|| -> Result<_> {
            let mut command = Command::new(&item.command[0]);
            command
                .args(&item.command[1..])
                .current_dir(&self.root)
                .stdin(Stdio::null())
                .stdout(File::create(&record.stdout)?)
                .stderr(File::create(&record.stderr)?);
            // SAFETY: only the async-signal-safe setsid syscall runs between fork/exec.
            unsafe {
                command.pre_exec(|| {
                    if libc::setsid() < 0 {
                        Err(io::Error::last_os_error())
                    } else {
                        Ok(())
                    }
                });
            }
            Ok(command.spawn()?)
        })();
        let child = match spawn {
            Ok(child) => child,
            Err(error) => {
                record.state = "failed".into();
                record.error = Some(error.to_string());
                record.ended = Some(store::now());
                self.store.save_run(&record)?;
                return Ok(Some(record));
            }
        };
        let mut owned = OwnedChild::new(child);
        record.pgid = Some(owned.child.id() as i32);
        record.state = "running".into();
        self.store.save_run(&record)?;
        drop(config);
        let status = loop {
            if self.stopped.load(Ordering::Relaxed) {
                owned.stop()?;
                record.state = "interrupted".into();
                break owned.child.wait()?;
            }
            if let Some(status) = owned.child.try_wait()? {
                owned.stop()?;
                record.state = if status.success() {
                    "succeeded"
                } else {
                    "failed"
                }
                .into();
                break status;
            }
            thread::sleep(Duration::from_millis(25));
        };
        record.exit_code = Some(process::code(status));
        record.ended = Some(store::now());
        self.store.save_run(&record)?;
        Ok(Some(record))
    }
    pub fn handle(&self, action: Action) -> Result<i32> {
        match action {
            Action::Add { .. }
            | Action::Pause { .. }
            | Action::Resume { .. }
            | Action::Remove { .. } => self.edit(action)?,
            Action::List => self.listing()?,
            Action::Runs { id } => {
                let mut records: Vec<_> = self
                    .store
                    .records()?
                    .into_iter()
                    .filter(|r| id.as_ref().is_none_or(|id| *id == r.schedule_id))
                    .collect();
                records.sort_by(|a, b| b.started.total_cmp(&a.started));
                records.truncate(20);
                print_json(&records)?;
            }
            Action::Run { id } => {
                let record = self.run(Some(&id), false)?.context("Run was not started")?;
                let code = match record.state.as_str() {
                    "succeeded" => 0,
                    "interrupted" => 130,
                    _ => 1,
                };
                print_json(&record)?;
                return Ok(code);
            }
            Action::Serve => {
                let _guard = self.lock("serve.lock", false)?;
                println!(
                    "Scheduling commands in {}. Ctrl+C to stop.",
                    self.root.display()
                );
                io::stdout().flush()?;
                while !self.stopped.load(Ordering::Relaxed) {
                    if let Some(record) = self.run(None, true)? {
                        print_json(&record)?;
                    } else {
                        for _ in 0..10 {
                            if self.stopped.load(Ordering::Relaxed) {
                                break;
                            }
                            thread::sleep(Duration::from_millis(50));
                        }
                    }
                }
                return Ok(130);
            }
        }
        Ok(0)
    }
}
fn latest<'a>(item: &Definition, records: &'a [Run]) -> Option<&'a Run> {
    records
        .iter()
        .filter(|r| r.generation == item.generation)
        .max_by(|a, b| {
            a.started
                .total_cmp(&b.started)
                .then_with(|| a.run_id.cmp(&b.run_id))
        })
}
fn due_at(item: &Definition, records: &[Run]) -> Result<f64> {
    Ok(item.anchor.max(
        latest(item, records)
            .and_then(|r| r.ended)
            .unwrap_or(item.anchor),
    ) + store::interval(&item.every)?)
}
fn print_json(value: &impl Serialize) -> Result<()> {
    let mut out = io::stdout().lock();
    serde_json::to_writer_pretty(&mut out, value)?;
    writeln!(out)?;
    out.flush()?;
    Ok(())
}
