use anyhow::{bail, Context, Result};
use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};
use std::{
    collections::HashSet,
    fs::{self, File, OpenOptions},
    io::{self, Write},
    os::{fd::AsRawFd, unix::fs::OpenOptionsExt},
    path::{Path, PathBuf},
    sync::atomic::{AtomicBool, Ordering},
    thread,
    time::{Duration, SystemTime, UNIX_EPOCH},
};
use uuid::Uuid;

pub fn now() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("clock before epoch")
        .as_secs_f64()
}
pub fn uuid() -> String {
    Uuid::new_v4().simple().to_string()
}
pub fn valid_id(s: &str) -> bool {
    !s.is_empty()
        && s.len() <= 64
        && s.as_bytes()[0].is_ascii_alphanumeric()
        && s.bytes()
            .all(|c| c.is_ascii_alphanumeric() || c == b'_' || c == b'-')
}
fn valid_uuid(s: &str) -> bool {
    s.len() == 32
        && s.bytes()
            .all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
}
fn valid_time(t: f64) -> bool {
    t.is_finite() && (0.0..1e11).contains(&t)
}
fn valid_command(command: &[String]) -> bool {
    !command.is_empty() && !command[0].is_empty() && command.iter().all(|s| !s.contains('\0'))
}
pub fn interval(s: &str) -> Result<f64> {
    if !s.is_ascii() {
        bail!("Interval must use ASCII digits and s, m, h, or d");
    }
    let (digits, unit) = s.split_at(s.len().saturating_sub(1));
    let factor = match unit {
        "s" => 1,
        "m" => 60,
        "h" => 3600,
        "d" => 86400,
        _ => 0,
    };
    if digits.is_empty()
        || digits.starts_with('0')
        || !digits.bytes().all(|c| c.is_ascii_digit())
        || factor == 0
    {
        bail!("Interval must be a positive integer followed by s, m, h, or d");
    }
    let n = digits
        .parse::<u64>()
        .ok()
        .and_then(|n| n.checked_mul(factor));
    match n {
        Some(n) if n <= 315360000 => Ok(n as f64),
        _ => bail!("Interval must not exceed ten years"),
    }
}

#[derive(Clone, Serialize, Deserialize)]
pub struct Definition {
    pub id: String,
    pub generation: String,
    pub every: String,
    pub command: Vec<String>,
    pub enabled: bool,
    pub anchor: f64,
    #[serde(flatten)]
    pub extra: Map<String, Value>,
}

#[derive(Clone, Serialize, Deserialize)]
pub struct Run {
    pub run_id: String,
    pub schedule_id: String,
    pub generation: String,
    pub command: Vec<String>,
    pub project: String,
    pub started: f64,
    pub ended: Option<f64>,
    pub state: String,
    pub exit_code: Option<i32>,
    pub pgid: Option<i32>,
    pub stdout: String,
    pub stderr: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
    #[serde(flatten)]
    pub extra: Map<String, Value>,
}
impl Run {
    pub fn active(&self) -> bool {
        self.state == "starting" || self.state == "running"
    }
}

pub struct Store {
    pub definitions: PathBuf,
    pub runtime: PathBuf,
}
impl Store {
    pub fn new(root: &Path) -> Self {
        Self {
            definitions: root.join(".sumi/schedules.json"),
            runtime: root.join(".sumi/schedule-runs"),
        }
    }
    pub fn load(&self) -> Result<Vec<Definition>> {
        if !self.definitions.try_exists()? {
            return Ok(vec![]);
        }
        let items: Vec<Definition> = serde_json::from_slice(&fs::read(&self.definitions)?)
            .with_context(|| {
                format!(
                    "Invalid schedule definitions: {}; file preserved",
                    self.definitions.display()
                )
            })?;
        let mut seen = HashSet::new();
        for item in &items {
            if !valid_id(&item.id)
                || !valid_uuid(&item.generation)
                || !valid_time(item.anchor)
                || !valid_command(&item.command)
                || interval(&item.every).is_err()
                || !seen.insert(&item.id)
            {
                bail!(
                    "Invalid schedule definitions: {}; file preserved",
                    self.definitions.display()
                );
            }
        }
        Ok(items)
    }
    pub fn records(&self) -> Result<Vec<Run>> {
        if !self.runtime.try_exists()? {
            return Ok(vec![]);
        }
        let mut paths = vec![];
        for entry in fs::read_dir(&self.runtime)? {
            let path = entry?.path().join("run.json");
            if path.is_file() {
                paths.push(path);
            }
        }
        paths.sort();
        let mut runs = vec![];
        for path in paths {
            let run: Run = serde_json::from_slice(&fs::read(&path)?).with_context(|| {
                format!("Cannot read {}; preserve it for recovery", path.display())
            })?;
            if !valid_uuid(&run.run_id)
                || !valid_uuid(&run.generation)
                || !valid_id(&run.schedule_id)
                || !valid_command(&run.command)
                || !valid_time(run.started)
                || run.ended.is_some_and(|t| !valid_time(t))
                || run.pgid.is_some_and(|p| p <= 1)
                || path
                    .parent()
                    .and_then(|p| p.file_name())
                    .and_then(|p| p.to_str())
                    != Some(&run.run_id)
                || !["starting", "running", "succeeded", "failed", "interrupted"]
                    .contains(&run.state.as_str())
            {
                bail!(
                    "Invalid run record {}; preserve it for recovery",
                    path.display()
                );
            }
            runs.push(run);
        }
        Ok(runs)
    }
    pub fn save_run(&self, run: &Run) -> Result<()> {
        atomic(&self.runtime.join(&run.run_id).join("run.json"), run)
    }
}

pub fn atomic(path: &Path, data: &impl Serialize) -> Result<()> {
    let parent = path.parent().context("Missing parent directory")?;
    fs::create_dir_all(parent)?;
    let temp = parent.join(format!(
        ".{}.{}",
        path.file_name().unwrap().to_string_lossy(),
        uuid()
    ));
    let result = (|| -> Result<()> {
        let mut file = OpenOptions::new()
            .write(true)
            .create_new(true)
            .mode(0o600)
            .open(&temp)?;
        serde_json::to_writer_pretty(&mut file, data)?;
        file.write_all(b"\n")?;
        file.sync_all()?;
        fs::rename(&temp, path)?;
        File::open(parent)?.sync_all()?;
        Ok(())
    })();
    let _ = fs::remove_file(temp);
    result
}

// File ownership holds the POSIX flock until drop; descriptors are close-on-exec.
pub struct Lock {
    _file: File,
}
impl Lock {
    pub fn acquire(path: &Path, blocking: bool, stopped: &AtomicBool) -> Result<Option<Self>> {
        fs::create_dir_all(path.parent().unwrap())?;
        let file = OpenOptions::new().create(true).append(true).open(path)?;
        loop {
            if stopped.load(Ordering::Relaxed) {
                bail!("Interrupted");
            }
            // SAFETY: fd is owned and valid; flock does not retain Rust memory.
            if unsafe { libc::flock(file.as_raw_fd(), libc::LOCK_EX | libc::LOCK_NB) } == 0 {
                return Ok(Some(Self { _file: file }));
            }
            let error = io::Error::last_os_error();
            if error.kind() == io::ErrorKind::Interrupted {
                continue;
            }
            if error.kind() != io::ErrorKind::WouldBlock {
                return Err(error.into());
            }
            if !blocking {
                return Ok(None);
            }
            thread::sleep(Duration::from_millis(50));
        }
    }
}
