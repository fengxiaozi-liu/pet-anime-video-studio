
const _genStageBounds = {
  preparing:    [0,   5,  "准备中"],
  rendering_cloud: [5,  75, "云端渲染中"],
  trying_cloud:    [75, 80, "尝试云端渲染"],
  rendering_local: [80, 95, "本地渲染中"],
  fallback_local:  [95, 98, "回退本地渲染"],
  done:            [100, 100, "完成"],
};

function _stageProgress(stage, elapsedInStage) {
  const [lo, hi, label] = _genStageBounds[stage] || [0, 0, stage];
  const span = hi - lo;
  // Estimate 45s per stage as a safe average for video generation
  const stageTotal = 45000;
  const pct = span > 0 ? lo + Math.min(span - 1, Math.round((elapsedInStage / stageTotal) * span)) : lo;
  return { pct: Math.min(pct, hi), label };
}

let _pollStartTime = 0;
let _currentStage = "preparing";
let _stageStartTime = 0;
let _progressInterval = null;

function startProgressSimulation() {
  stopProgressSimulation();
  _pollStartTime = Date.now();
  _stageStartTime = _pollStartTime;
  _currentStage = "preparing";
  
  const bar = document.getElementById("loading_progress_bar");
  if (bar) bar.style.display = "block";

  _progressInterval = setInterval(() => {
    const now = Date.now();
    const elapsedTotal = now - _pollStartTime;
    const elapsedInStage = now - _stageStartTime;
    
    const { pct, label } = _stageProgress(_currentStage, elapsedInStage);
    
    const fill = document.getElementById("loading_progress_fill");
    const textEl = document.getElementById("loading_text");
    const etaEl = document.getElementById("loading_eta");
    
    if (fill) fill.style.width = pct + "%";
    if (textEl && !textEl.textContent.startsWith("正在处理")) {
        textEl.textContent = `正在生成：${label}...`;
    }
    
    // Simple ETA: if we are at X%, and it took Yms, remaining is (Y/X * 100) - Y
    if (pct > 5) {
        const remainingMs = (elapsedTotal / pct) * (100 - pct);
        const remainingS = Math.round(remainingMs / 1000);
        if (etaEl) etaEl.textContent = `预计剩余: ${remainingS}s`;
    }
  }, 500);
}

function updateProgressStage(stage) {
    if (_currentStage !== stage && _genStageBounds[stage]) {
        _currentStage = stage;
        _stageStartTime = Date.now();
    }
}

function stopProgressSimulation() {
  if (_progressInterval) {
    clearInterval(_progressInterval);
    _progressInterval = null;
  }
}

function _showUploadProgress(pct, text) {
  const fill = document.getElementById("loading_progress_fill");
  const bar  = document.getElementById("loading_progress_bar");
  const textEl = document.getElementById("loading_text");
  const etaEl = document.getElementById("loading_eta");
  if (fill) fill.style.width = pct + "%";
  if (bar)  bar.style.display = "block";
  if (textEl) textEl.textContent = text;
  if (etaEl)  etaEl.textContent = pct < 100 ? `上传中: ${pct}%` : "";
}

function uploadWithProgress(fd) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/jobs", true);
    
    // Set headers if any (auth is handled by browser for basic auth usually, 
    // but if it's manual we'd add it here)
    
    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable) {
        const pct = Math.round((e.loaded / e.total) * 100);
        _showUploadProgress(pct, "正在上传图片...");
      }
    });
    
    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
            resolve(JSON.parse(xhr.responseText));
        } catch (e) {
            reject(new Error("Invalid server response"));
        }
      } else {
        let errorDetail = "Upload failed";
        try {
            const data = JSON.parse(xhr.responseText);
            errorDetail = data.detail || errorDetail;
        } catch(e) {}
        reject(new Error(errorDetail));
      }
    });
    
    xhr.addEventListener("error", () => reject(new Error("Network error during upload")));
    xhr.send(fd);
  });
}
