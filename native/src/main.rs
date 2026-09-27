mod process;
mod schedule;
mod store;

use anyhow::{bail, Context, Result};
use clap::{Parser, Subcommand};
use std::{
    path::PathBuf,
    process::Command,
    sync::{
        atomic::{AtomicBool, Ordering},
        Arc,
    },
};

#[derive(Parser)]
#[command(
    version,
    about = "Sumi native scheduling preview (other commands remain in bin/sumi)"
)]
struct Cli {
    #[arg(long)]
    root: Option<PathBuf>,
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Schedule local noninteractive commands; no agent or mux required.
    Schedule {
        #[command(subcommand)]
        action: Action,
    },
}

#[derive(Subcommand)]
pub enum Action {
    Add {
        id: String,
        #[arg(long)]
        every: String,
        #[arg(last = true, required = true, num_args = 1..)]
        command: Vec<String>,
    },
    List,
    Pause {
        id: String,
    },
    Resume {
        id: String,
    },
    Remove {
        id: String,
    },
    Run {
        id: String,
    },
    Runs {
        id: Option<String>,
    },
    Serve,
}

fn root(explicit: Option<PathBuf>) -> Result<PathBuf> {
    let path = if let Some(path) = explicit {
        if path.starts_with("~") {
            PathBuf::from(std::env::var_os("HOME").context("HOME is unset")?)
                .join(path.strip_prefix("~")?)
        } else {
            path
        }
    } else {
        Command::new("git")
            .args(["rev-parse", "--show-toplevel"])
            .output()
            .ok()
            .filter(|o| o.status.success())
            .map(|o| PathBuf::from(String::from_utf8_lossy(&o.stdout).trim()))
            .unwrap_or(std::env::current_dir()?)
    };
    let path = path
        .canonicalize()
        .context("Project directory does not exist")?;
    if !path.is_dir() {
        bail!("Project root must be a directory");
    }
    Ok(path)
}

fn main() {
    let cli = Cli::parse();
    let stopped = Arc::new(AtomicBool::new(false));
    let result = (|| {
        signal_hook::flag::register(signal_hook::consts::SIGINT, stopped.clone())?;
        signal_hook::flag::register(signal_hook::consts::SIGTERM, stopped.clone())?;
        let Commands::Schedule { action } = cli.command;
        schedule::Scheduler::new(root(cli.root)?, stopped.clone()).handle(action)
    })();
    let code = match result {
        Ok(code) => code,
        Err(error) => {
            eprintln!("sumi: {error:#}");
            if stopped.load(Ordering::Relaxed) {
                130
            } else {
                1
            }
        }
    };
    std::process::exit(code);
}
