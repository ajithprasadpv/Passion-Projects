/**
 * Timer functionality for the mock test simulator
 * Handles countdown timer, auto-submit, and time management
 */

class TestTimer {
    constructor(duration, onTimeUp, onTick) {
        this.duration = duration; // in seconds
        this.timeLeft = duration;
        this.onTimeUp = onTimeUp;
        this.onTick = onTick;
        this.interval = null;
        this.isRunning = false;
    }

    start() {
        if (this.isRunning) return;
        
        this.isRunning = true;
        this.interval = setInterval(() => {
            this.timeLeft--;
            
            if (this.onTick) {
                this.onTick(this.timeLeft);
            }
            
            if (this.timeLeft <= 0) {
                this.stop();
                if (this.onTimeUp) {
                    this.onTimeUp();
                }
            }
        }, 1000);
    }

    stop() {
        if (this.interval) {
            clearInterval(this.interval);
            this.interval = null;
        }
        this.isRunning = false;
    }

    pause() {
        this.stop();
    }

    resume() {
        if (this.timeLeft > 0) {
            this.start();
        }
    }

    getTimeLeft() {
        return this.timeLeft;
    }

    setTimeLeft(seconds) {
        this.timeLeft = Math.max(0, seconds);
    }

    formatTime(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;

        if (hours > 0) {
            return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        } else {
            return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }
    }

    getWarningLevel() {
        const percentage = (this.timeLeft / this.duration) * 100;
        
        if (percentage <= 5) return 'critical'; // Last 5%
        if (percentage <= 10) return 'danger';  // Last 10%
        if (percentage <= 25) return 'warning'; // Last 25%
        return 'normal';
    }
}

// Timer utilities
const TimerUtils = {
    /**
     * Create a visual timer display element
     */
    createTimerDisplay(containerId, timer) {
        const container = document.getElementById(containerId);
        if (!container) return null;

        const display = document.createElement('div');
        display.className = 'timer-display';
        display.innerHTML = `
            <div class="timer-icon">
                <i class="fas fa-clock"></i>
            </div>
            <div class="timer-text">
                <span class="time-value">${timer.formatTime(timer.getTimeLeft())}</span>
                <span class="time-label">remaining</span>
            </div>
        `;

        container.appendChild(display);
        return display;
    },

    /**
     * Update timer display with current time and styling
     */
    updateTimerDisplay(display, timer) {
        if (!display) return;

        const timeValue = display.querySelector('.time-value');
        const warningLevel = timer.getWarningLevel();
        
        // Update time text
        timeValue.textContent = timer.formatTime(timer.getTimeLeft());
        
        // Update styling based on warning level
        display.className = `timer-display timer-${warningLevel}`;
        
        // Add pulsing animation for critical time
        if (warningLevel === 'critical') {
            display.classList.add('timer-pulse');
        }
    },

    /**
     * Show auto-submit warning modal
     */
    showAutoSubmitWarning(timeLeft, onConfirm, onCancel) {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header bg-warning">
                        <h5 class="modal-title">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            Time Running Out!
                        </h5>
                    </div>
                    <div class="modal-body text-center">
                        <p class="mb-3">Only <strong>${Math.ceil(timeLeft / 60)} minutes</strong> remaining!</p>
                        <p>The test will be automatically submitted when time expires.</p>
                        <div class="alert alert-info">
                            <i class="fas fa-info-circle me-2"></i>
                            Make sure to review your answers before time runs out.
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-primary" data-bs-dismiss="modal">
                            Continue Test
                        </button>
                        <button type="button" class="btn btn-success" onclick="submitTestNow()">
                            Submit Now
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();
        
        // Clean up modal after it's hidden
        modal.addEventListener('hidden.bs.modal', () => {
            document.body.removeChild(modal);
        });
        
        return bootstrapModal;
    },

    /**
     * Handle page visibility changes (tab switching detection)
     */
    setupVisibilityHandler(onVisibilityChange) {
        document.addEventListener('visibilitychange', () => {
            if (onVisibilityChange) {
                onVisibilityChange(document.hidden);
            }
        });
    },

    /**
     * Prevent page unload during active test
     */
    setupUnloadPrevention(isActive) {
        const handler = (e) => {
            if (isActive()) {
                e.preventDefault();
                e.returnValue = 'Are you sure you want to leave the test? Your progress may be lost.';
                return e.returnValue;
            }
        };

        window.addEventListener('beforeunload', handler);
        
        // Return cleanup function
        return () => {
            window.removeEventListener('beforeunload', handler);
        };
    }
};

// Auto-save functionality
class AutoSave {
    constructor(saveInterval = 30000) { // 30 seconds default
        this.saveInterval = saveInterval;
        this.interval = null;
        this.lastSave = Date.now();
        this.pendingData = null;
    }

    start(saveFunction) {
        if (this.interval) return;
        
        this.saveFunction = saveFunction;
        this.interval = setInterval(() => {
            if (this.pendingData && this.saveFunction) {
                this.saveFunction(this.pendingData);
                this.lastSave = Date.now();
                this.pendingData = null;
            }
        }, this.saveInterval);
    }

    stop() {
        if (this.interval) {
            clearInterval(this.interval);
            this.interval = null;
        }
    }

    markForSave(data) {
        this.pendingData = data;
    }

    forceSave() {
        if (this.pendingData && this.saveFunction) {
            this.saveFunction(this.pendingData);
            this.lastSave = Date.now();
            this.pendingData = null;
        }
    }
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { TestTimer, TimerUtils, AutoSave };
}
