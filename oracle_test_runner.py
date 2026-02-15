#!/usr/bin/env python3
"""
ORACLE TEST RUNNER - Complete Autonomous Testing System

Watches for BUILD_AND_TEST command from Jules/Windows
Builds JAR, runs with Tor, monitors, kills after 20min, uploads results

Author: Autonomous Bot Factory
Date: Feb 14, 2026
"""

import os
import sys
import json
import time
import subprocess
import signal
from pathlib import Path
from datetime import datetime
import shutil

# =============================================================================
# CONFIGURATION
# =============================================================================

# Paths
AI_BRIDGE_REPO = Path.home() / 'ai-bridge-repo'
PROJECT_DIR = Path.home() / 'Microbot-NewBot'
BUILD_ARTIFACTS = Path.home() / 'oracle_build_artifacts'
SCREENSHOT_DIR = Path.home() / 'microbot-screenshots'

# Commands directory for Jules to trigger builds
COMMANDS_DIR = AI_BRIDGE_REPO / 'commands'
RESULTS_DIR = AI_BRIDGE_REPO / 'test-results'

# Test configuration
TEST_DURATION_SECONDS = 1200  # 20 minutes
CHECK_INTERVAL = 5  # Check for commands every 5s

# Tor proxy settings
TOR_HOST = "127.0.0.1"
TOR_PORT = "9150"

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def log(message):
    """Print with timestamp"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] {message}")

def git_pull():
    """Pull latest from GitHub"""
    try:
        subprocess.run(['git', 'pull'], cwd=AI_BRIDGE_REPO, capture_output=True, timeout=30)
    except:
        pass

def git_push(message="Test results"):
    """Push to GitHub"""
    try:
        subprocess.run(['git', 'add', '.'], cwd=AI_BRIDGE_REPO, timeout=10)
        subprocess.run(['git', 'commit', '-m', message], cwd=AI_BRIDGE_REPO, timeout=10)
        subprocess.run(['git', 'push'], cwd=AI_BRIDGE_REPO, timeout=30)
        return True
    except Exception as e:
        log(f"Git push failed: {e}")
        return False

def cleanup_old_screenshots():
    """Clear old screenshots before new test"""
    if SCREENSHOT_DIR.exists():
        for file in SCREENSHOT_DIR.glob('*.png'):
            try:
                file.unlink()
            except:
                pass
        log(f"Cleared old screenshots from {SCREENSHOT_DIR}")

# =============================================================================
# BUILD SYSTEM
# =============================================================================

def run_maven_build():
    """
    Run Maven build using HeadlessBuilder
    Returns: (success: bool, jar_path: str or None)
    """
    log("🔨 Starting Maven build...")
    
    try:
        # Run the headless builder script
        result = subprocess.run(
            ['python3', 'headless_builder.py'],
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )
        
        if result.returncode != 0:
            log("❌ Build FAILED!")
            log(f"Error: {result.stdout[-500:]}")
            return False, None
        
        log("✅ Build SUCCESS!")
        
        # Find the generated JAR
        artifacts = list(BUILD_ARTIFACTS.glob('artifacts_*/main_runelite-client-*.jar'))
        
        if not artifacts:
            log("⚠️ No JAR found in artifacts!")
            return False, None
        
        # Get most recent
        jar_path = max(artifacts, key=lambda p: p.stat().st_mtime)
        
        log(f"📦 JAR located: {jar_path.name}")
        
        return True, jar_path
        
    except Exception as e:
        log(f"❌ Build error: {e}")
        return False, None

# =============================================================================
# TEST RUNNER
# =============================================================================

class BotTestRunner:
    """Manages bot testing lifecycle"""
    
    def __init__(self, jar_path):
        self.jar_path = jar_path
        self.process = None
        self.start_time = None
        self.log_file = None
    
    def start(self):
        """Launch the bot with Tor proxy"""
        log("\n🚀 LAUNCHING BOT...")
        log(f"JAR: {self.jar_path}")
        log(f"Proxy: {TOR_HOST}:{TOR_PORT}")
        log(f"Duration: {TEST_DURATION_SECONDS}s")
        
        # Java command with Tor proxy
        cmd = [
            'java',
            f'-DsocksProxyHost={TOR_HOST}',
            f'-DsocksProxyPort={TOR_PORT}',
            '-Djava.net.preferIPv4Stack=true',
            '-jar',
            str(self.jar_path)
        ]
        
        # Create log file
        self.log_file = AI_BRIDGE_REPO / f'client_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        
        try:
            # Launch process, redirect output to log
            with open(self.log_file, 'w') as log_f:
                self.process = subprocess.Popen(
                    cmd,
                    stdout=log_f,
                    stderr=subprocess.STDOUT,
                    preexec_fn=os.setsid  # Create new process group for easy killing
                )
            
            self.start_time = time.time()
            log(f"✅ Bot started (PID: {self.process.pid})")
            log(f"📝 Logging to: {self.log_file.name}")
            
            return True
            
        except Exception as e:
            log(f"❌ Failed to start bot: {e}")
            return False
    
    def is_running(self):
        """Check if bot is still running"""
        if self.process is None:
            return False
        return self.process.poll() is None
    
    def get_runtime(self):
        """Get runtime in seconds"""
        if self.start_time:
            return int(time.time() - self.start_time)
        return 0
    
    def kill(self):
        """Force kill the bot process"""
        if self.process and self.is_running():
            try:
                # Kill entire process group (handles child processes too)
                os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                log("🛑 Bot process killed")
            except Exception as e:
                log(f"⚠️ Error killing process: {e}")

# =============================================================================
# RESULTS HANDLER
# =============================================================================

def collect_and_upload_results(test_runner, test_id):
    """
    Collect screenshots and logs, upload to GitHub
    Returns: dict with test results
    """
    log("\n📊 COLLECTING RESULTS...")
    
    # Create results directory for this test
    test_results_dir = RESULTS_DIR / test_id
    test_results_dir.mkdir(parents=True, exist_ok=True)
    
    results = {
        'test_id': test_id,
        'timestamp': datetime.now().isoformat(),
        'duration_seconds': test_runner.get_runtime(),
        'screenshots_count': 0,
        'log_file': None,
        'status': 'completed'
    }
    
    # 1. Collect screenshots
    if SCREENSHOT_DIR.exists():
        screenshots = list(SCREENSHOT_DIR.glob('*.png'))
        
        if screenshots:
            log(f"📸 Found {len(screenshots)} screenshots")
            
            # Copy to results directory
            for i, screenshot in enumerate(screenshots, 1):
                dest = test_results_dir / f"screenshot_{i:03d}.png"
                shutil.copy(screenshot, dest)
            
            results['screenshots_count'] = len(screenshots)
        else:
            log("⚠️ No screenshots found (plugin may be disabled)")
    
    # 2. Collect log file
    if test_runner.log_file and test_runner.log_file.exists():
        log(f"📝 Processing log file...")
        
        # Filter out cache warnings
        filtered_log = test_results_dir / 'client_filtered.log'
        
        with open(test_runner.log_file, 'r') as src:
            with open(filtered_log, 'w') as dst:
                for line in src:
                    # Skip cache warnings
                    if 'cache' not in line.lower() or 'warning' not in line.lower():
                        dst.write(line)
        
        results['log_file'] = filtered_log.name
        log(f"✅ Log filtered and saved")
    
    # 3. Save results metadata
    metadata_file = test_results_dir / 'results.json'
    with open(metadata_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    log(f"💾 Results saved to: {test_results_dir}")
    
    # 4. Push to GitHub
    log("📤 Uploading to GitHub...")
    
    if git_push(f"Test results: {test_id}"):
        log("✅ Results uploaded!")
    else:
        log("⚠️ Upload failed")
    
    return results

# =============================================================================
# ANALYSIS REQUEST
# =============================================================================

def request_analysis(test_id):
    """
    Send task to Windows to analyze test results
    """
    log("\n🤖 REQUESTING AI ANALYSIS...")
    
    task = {
        'id': f'analyze_{test_id}',
        'ai': 'gemini_1',  # or 'claude' if screenshots need vision
        'prompt': f"""
Analyze test results for: {test_id}

Results are in: test-results/{test_id}/

Review:
1. Screenshots (if any) - is bot working correctly?
2. Client log - any errors or warnings?

Provide:
- Status: WORKING / STUCK / ERROR
- Issues found (if any)
- Suggested fixes (if needed)

Be concise.
"""
    }
    
    task_file = AI_BRIDGE_REPO / 'tasks' / f'task_analyze_{test_id}.json'
    with open(task_file, 'w') as f:
        json.dump(task, f, indent=2)
    
    git_push(f"Analysis request: {test_id}")
    
    log(f"✅ Analysis task sent to Windows")

# =============================================================================
# MAIN TEST ORCHESTRATOR
# =============================================================================

def run_test_cycle(command):
    """
    Complete test cycle:
    1. Build
    2. Run for 20 min
    3. Kill
    4. Upload results
    5. Request analysis
    """
    test_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    log("\n" + "="*60)
    log(f"🏁 STARTING TEST CYCLE: {test_id}")
    log("="*60)
    
    # Step 1: Build
    success, jar_path = run_maven_build()
    
    if not success:
        log("❌ Build failed - aborting test")
        return
    
    # Step 2: Prepare
    cleanup_old_screenshots()
    SCREENSHOT_DIR.mkdir(exist_ok=True)
    
    # Step 3: Run test
    runner = BotTestRunner(jar_path)
    
    if not runner.start():
        log("❌ Failed to start bot")
        return
    
    # Step 4: Monitor
    log(f"\n⏱️ TEST RUNNING (will auto-kill after {TEST_DURATION_SECONDS}s)...")
    
    start_time = time.time()
    last_update = 0
    
    while True:
        elapsed = int(time.time() - start_time)
        
        # Show progress every 60s
        if elapsed - last_update >= 60:
            log(f"⏱️ Runtime: {elapsed}s / {TEST_DURATION_SECONDS}s")
            last_update = elapsed
        
        # Check if time's up
        if elapsed >= TEST_DURATION_SECONDS:
            log(f"\n✅ Test duration complete ({elapsed}s)")
            break
        
        # Check if process crashed
        if not runner.is_running():
            log(f"\n⚠️ Bot process ended early (after {elapsed}s)")
            break
        
        time.sleep(5)
    
    # Step 5: Kill process
    runner.kill()
    time.sleep(2)
    
    # Step 6: Collect and upload results
    results = collect_and_upload_results(runner, test_id)
    
    # Step 7: Request analysis
    request_analysis(test_id)
    
    log("\n" + "="*60)
    log(f"✅ TEST CYCLE COMPLETE: {test_id}")
    log("="*60)
    log(f"Screenshots: {results['screenshots_count']}")
    log(f"Duration: {results['duration_seconds']}s")
    log(f"Results uploaded to: test-results/{test_id}/")
    log(f"Analysis requested from AI")
    log("="*60 + "\n")

# =============================================================================
# COMMAND WATCHER
# =============================================================================

def watch_for_commands():
    """
    Main loop - watches for BUILD_AND_TEST commands from Jules/Windows
    """
    log("""
╔══════════════════════════════════════════════════════════════╗
║              ORACLE TEST RUNNER v1.0                         ║
║           Autonomous Bot Testing System                      ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Ensure directories exist
    COMMANDS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    log(f"📁 Watching: {COMMANDS_DIR}")
    log(f"📁 Results: {RESULTS_DIR}")
    log(f"🔄 Polling every {CHECK_INTERVAL}s")
    log("\n👀 Waiting for BUILD_AND_TEST command...\n")
    
    while True:
        try:
            # Pull from GitHub
            git_pull()
            
            # Check for command files
            command_files = list(COMMANDS_DIR.glob('*.json'))
            
            for cmd_file in command_files:
                try:
                    # Read command
                    with open(cmd_file) as f:
                        command = json.load(f)
                    
                    log(f"\n🔔 COMMAND RECEIVED: {cmd_file.name}")
                    log(f"Command: {command}")
                    
                    # Delete command file
                    cmd_file.unlink()
                    
                    # Execute test cycle
                    run_test_cycle(command)
                    
                    log("\n👀 Waiting for next command...\n")
                    
                except Exception as e:
                    log(f"❌ Error processing command: {e}")
            
            # Sleep before next check
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            log("\n\n👋 Shutting down Oracle Test Runner...")
            break
        
        except Exception as e:
            log(f"\n⚠️ Error in main loop: {e}")
            time.sleep(CHECK_INTERVAL)

# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    watch_for_commands()
