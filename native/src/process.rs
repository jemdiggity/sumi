use anyhow::{bail, Result};
use std::{
    io,
    os::unix::process::ExitStatusExt,
    process::{Child, ExitStatus},
    thread,
    time::{Duration, Instant},
};

pub fn group_alive(pgid: i32) -> Result<bool> {
    if pgid <= 1 {
        bail!("Invalid process group {pgid}");
    }
    // SAFETY: signal 0 checks existence, positive pgid was validated.
    if unsafe { libc::killpg(pgid, 0) } == 0 {
        return Ok(true);
    }
    let error = io::Error::last_os_error();
    match error.raw_os_error() {
        Some(libc::ESRCH) => Ok(false),
        Some(libc::EPERM) => Ok(true),
        _ => Err(error.into()),
    }
}
fn signal_group(pgid: i32, signal: i32) -> Result<()> {
    if pgid <= 1 {
        bail!("Invalid process group {pgid}");
    }
    // SAFETY: targets the owned child group; no pointers cross the FFI boundary.
    if unsafe { libc::killpg(pgid, signal) } != 0 {
        let error = io::Error::last_os_error();
        if error.raw_os_error() != Some(libc::ESRCH) {
            return Err(error.into());
        }
    }
    Ok(())
}
pub fn code(status: ExitStatus) -> i32 {
    status
        .code()
        .unwrap_or_else(|| -status.signal().unwrap_or(1))
}

pub struct OwnedChild {
    pub child: Child,
    cleaned: bool,
}
impl OwnedChild {
    pub fn new(child: Child) -> Self {
        Self {
            child,
            cleaned: false,
        }
    }
    pub fn stop(&mut self) -> Result<()> {
        let pgid = self.child.id() as i32;
        self.child.try_wait()?;
        if group_alive(pgid)? {
            signal_group(pgid, libc::SIGTERM)?;
            self.wait_group(Duration::from_secs(2))?;
            if group_alive(pgid)? {
                signal_group(pgid, libc::SIGKILL)?;
                self.wait_group(Duration::from_secs(2))?;
            }
        }
        if group_alive(pgid)? {
            bail!("Process group {pgid} survived cleanup; run requires recovery. Inspect the run and stop surviving processes before retrying.");
        }
        self.child.wait()?;
        self.cleaned = true;
        Ok(())
    }
    fn wait_group(&mut self, grace: Duration) -> Result<()> {
        let deadline = Instant::now() + grace;
        while group_alive(self.child.id() as i32)? && Instant::now() < deadline {
            self.child.try_wait()?;
            thread::sleep(Duration::from_millis(50));
        }
        Ok(())
    }
}
impl Drop for OwnedChild {
    fn drop(&mut self) {
        if !self.cleaned {
            if let Err(error) = self.stop() {
                eprintln!("sumi: {error}");
            }
        }
    }
}
