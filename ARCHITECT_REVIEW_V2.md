# Architect Review V2 — Pet Anime Video Project
**Date:** 2026-03-21 | **Status:** 4 days overdue, ~85% complete

---

## 1. Current State Assessment

### ✅ What's Working
| Component | Status | Notes |
|-----------|--------|-------|
| Backend API | ✅ Stable | FastAPI with proper schema validation (Pydantic Storyboard model) |
| Job Queue | ✅ Working | JobStore with async processing via `run_job()` |
| Error Handling | ✅ Recent | `parseErrorResponse()` added to app.js, HTTPException chain in place |
| Authentication | ✅ Ready | HTTP Basic Auth + rate limiting (10/min, 100/hour) |
| Platform Templates | ✅ Complete | Kling/OpenAI/Gemini/Doubao provider dispatch |
| File Upload | ✅ Functional | Image validation, BGM support, asset storage |

### ⚠️ Gaps / Risks

| Issue | Impact | Priority |
|-------|--------|----------|
| **No loading states on UI** | Users have no feedback during upload/generation → feels broken | 🔴 Critical |
| No progress indicators for long-running jobs | Can't distinguish "working" from "stuck" | 🟠 High |
| No E2E tests | Can't verify staging before production | 🟠 High |
| No explicit API response validation on frontend | Trusting backend implicitly | 🟡 Medium |
| Uncommitted changes (5 files) | Risk of merge conflicts, unclear state | 🟡 Medium |

---

## 2. Single Highest-Leverage Item

### 🎯 Loading States + Progress Indicators

**Why this wins:**
- Fixes the #1 user-facing problem (no feedback = perceived as broken)
- Small scope, high visibility (~30 min work)
- Enables all subsequent testing/validation work to be observable
- Professional quality differentiator — staging deployment without this looks amateur

**Impact matrix:**
```
User Experience:      ████████████ (90% improvement)
Implementation Effort: ██ (10% of remaining work)
Risk Reduction:       ████ (moderate)
```

---

## 3. Concrete Implementation Plan

### Phase 1: Core Loading States (20 min)

#### A. Update `static/app.js`

**Add spinner CSS class to existing elements:**

```javascript
// After line ~90 (sleep function), add:
function setLoading(selector, isLoading, message = null) {
    const el = document.querySelector(selector);
    if (!el) return;
    
    if (isLoading) {
        el.dataset.loading = "true";
        if (message) el.dataset.loadingMessage = message;
    } else {
        delete el.dataset.loading;
        delete el.dataset.loadingMessage;
    }
}

// Wrap file selection area
const dropZone = document.getElementById('drop-zone');
const submitBtn = document.getElementById('submit-btn');

// On form submit (modify createJob function around line 240):
async function createJob(formData) {
    setLoading('#submit-btn', true, 'Generating...');
    setLoading('#drop-zone', true);
    
    try {
        // ... existing fetch logic ...
    } catch (err) {
        log(`Error: ${err.message}`);
    } finally {
        setLoading('#submit-btn', false);
        setLoading('#drop-zone', false);
    }
}
```

**Modify existing async functions:**

```javascript
// In poll() function (line 107):
async function poll(jobId, onUpdate) {
    setLoading(`[data-job-id="${jobId}"] .status`, true, 'Processing...');
    
    let attempts = 0;
    while (attempts < 100) {
        try {
            const res = await fetch(`/api/jobs/${jobId}`, { cache: "no-store" });
            if (!res.ok) throw new Error(await parseErrorResponse(res));
            const job = await res.json();
            
            onUpdate?.(job);
            
            if (job.status === 'done' || job.status === 'error') {
                setLoading(`[data-job-id="${jobId}"] .status`, false);
                break;
            }
            
            await sleep(1500);
            attempts++;
        } catch (err) {
            console.error('Poll error:', err);
            await sleep(2000);
            attempts++;
        }
    }
}
```

#### B. Add Loading Spinner CSS to `static/ui-improvements.css`

```css
/* Loading Spinner Styles */
button[data-loading="true"],
div[data-loading="true"] {
    position: relative;
    pointer-events: none;
    opacity: 0.7;
}

button[data-loading="true"]::after,
div[data-loading="true"]::after {
    content: "";
    position: absolute;
    width: 16px;
    height: 16px;
    top: 50%;
    right: 8px;
    margin-top: -8px;
    border: 2px solid #fff;
    border-top-color: transparent;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

/* Loading overlay for drop zone */
#drop-zone[data-loading="true"] {
    background-color: rgba(0, 0, 0, 0.05);
    cursor: wait;
}

#drop-zone[data-loading-message]::before {
    content: attr(data-loading-message);
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    font-weight: 600;
    color: #333;
}

/* Job status loading indicator */
.job-card [data-loading="true"].status {
    color: #666;
    font-style: italic;
}

.job-card [data-loading="true"].status::before {
    content: "⏳ ";
}
```

---

### Phase 2: Progress Indicators (10 min)

#### A. Add progress bar element to `templates/index.html`

In the job card template, add after status line:

```html
<div class="progress-container" style="display: none;">
    <div class="progress-bar" style="width: 0%"></div>
</div>
```

#### B. Update polling to report progress

```javascript
// In poll() function, track status transitions:
async function poll(jobId, onUpdate) {
    const statusMap = { queued: 0, started: 30, generating: 60, compiling: 80, done: 100 };
    let lastStatus = null;
    
    // ... inside loop after fetching job:
    const progress = statusMap[job.status] ?? 50;
    const progressEl = document.querySelector(`[data-job-id="${jobId}"] .progress-bar`);
    if (progressEl && job.status !== lastStatus) {
        progressEl.style.width = `${progress}%`;
        progressEl.previousElementSibling.style.display = 'block';
    }
    lastStatus = job.status;
}
```

#### C. Add progress bar CSS to `ui-improvements.css`

```css
.progress-container {
    width: 100%;
    height: 4px;
    background-color: #e0e0e0;
    border-radius: 2px;
    overflow: hidden;
    margin-top: 8px;
}

.progress-bar {
    height: 100%;
    background: linear-gradient(90deg, #ff6b6b, #feca57);
    transition: width 0.3s ease;
}
```

---

### Phase 3: API Response Validation (5 min)

```javascript
// Add to app.js after parseErrorResponse:
function validateJobResponse(job) {
    const requiredFields = ['id', 'status', 'prompt'];
    const missing = requiredFields.filter(f => !(f in job));
    if (missing.length > 0) {
        console.warn(`Missing job fields: ${missing.join(', ')}`);
        return false;
    }
    
    // Validate status transitions
    const validStatuses = ['queued', 'started', 'generating', 'compiling', 'done', 'error'];
    if (!validStatuses.includes(job.status)) {
        console.error(`Invalid job status: ${job.status}`);
        return false;
    }
    
    return true;
}

// Use in poll():
const job = await res.json();
if (!validateJobResponse(job)) {
    throw new Error('Invalid job response structure');
}
```

---

## 4. Acceptance Criteria

### ✅ Definition of Done

| Criterion | Test Method | Expected Result |
|-----------|-------------|-----------------|
| Submit button shows spinner on click | Click submit, observe UI | Spinner appears, button disabled |
| Drop zone visually busy during upload | Select images, watch drop zone | Overlay appears with "Uploading..." |
| Job cards show processing state | Start generation, observe card | Status shows "⏳ Processing..." |
| Progress bar advances through stages | Monitor job card | Bar fills: 0% → 30% → 60% → 80% → 100% |
| Invalid API response handled gracefully | Return malformed JSON | User sees error, not blank/crash |
| All loading states reset on completion | Wait for job.done | Spinning stops, buttons re-enabled |

### 📋 Verification Commands

```bash
# Frontend syntax check
npx eslint static/app.js

# Manual test sequence
1. Open http://localhost:8000
2. Select 3 images
3. Click "Generate Video"
   → Should see spinner on button
   → Should see overlay on drop zone
   → Job list should update with pending job
   → Job card should show progress indicator
4. Wait for completion (~30-60s)
   → Progress reaches 100%
   → Video download link appears
```

---

## 5. Remaining Work Summary

After completing loading states, here's what remains to reach 100% professional quality:

| Item | Est. Time | Priority |
|------|-----------|----------|
| E2E Test Suite (Playwright) | 2 hours | 🟠 High |
| Staging Docker Compose Config | 30 min | 🟠 High |
| Commit uncommitted changes | 10 min | 🟡 Medium |
| Documentation cleanup | 30 min | 🟢 Low |

**Total remaining time: ~3 hours**

---

## Decision Log

**2026-03-21**: Prioritized loading states over E2E tests because:
1. User-perceived value is immediate
2. Makes all other functionality demonstrable
3. Low risk, fast delivery
4. E2E tests can run against "working but ugly" → now we fix "ugly" first
