const $ = (id) => document.getElementById(id);

// Error tracking for debugging
let errorHistory = [];

function logError(context, details = {}) {
  const entry = {
    timestamp: new Date().toISOString(),
    context,
    ...details
  };
  errorHistory.push(entry);
  console.error(`[ERROR] ${context}:`, details);
}

function showErrorMessage(userMessage, technicalDetails = null) {
  // Show user-friendly message
  alert(userMessage);
  
  // Log technical details for debugging
  if (technicalDetails) {
    logError('User-facing error', { message: userMessage, details: technicalDetails });
  }
}

function log(msg) {
  const el = $("log");
  el.textContent += msg + "\n";
  el.scrollTop = el.scrollHeight;
}

function setGlobalStatus(text, kind = "idle") {
  const el = $("global_status");
  if (!el) return;
  el.textContent = text;
  el.dataset.kind = kind;
  const map = {
    idle: { bg: "#fff", color: "#8b7768", border: "#efd9c8" },
    running: { bg: "#f5f2ff", color: "#5d4be0", border: "#c7bafc" },
    done: { bg: "#effbf4", color: "#12794a", border: "#bde7cf" },
    error: { bg: "#fff1f1", color: "#c33c3c", border: "#f4b7b7" },
  };
  const s = map[kind] || map.idle;
  el.style.background = s.bg;
  el.style.color = s.color;
  el.style.borderColor = s.border;
}

function setDownloadState(enabled, href = "#") {
  const el = $("download_mp4");
  if (!el) return;
  el.href = href;
  el.setAttribute("aria-disabled", enabled ? "false" : "true");
  el.classList.toggle("is-disabled", !enabled);
  if (enabled) {
    el.removeAttribute("tabindex");
  } else {
    el.setAttribute("tabindex", "-1");
  }
}

function renderJobMeta(job) {
  const el = $("job_meta");
  if (!el) return;
  if (!job) {
    el.textContent = "";
    return;
  }

  const lines = [];
  if (job.stage) lines.push(`阶段：${job.stage}`);
  if (job.template_name) lines.push(`模板：${job.template_name}`);
  if (job.effective_backend) lines.push(`实际链路：${job.effective_backend}`);
  if (job.effective_provider) lines.push(`实际提供商：${job.effective_provider}`);
  if (job.image_count) lines.push(`图片数：${job.image_count}`);
  if (job.fallback_reason) lines.push(`回退原因：${job.fallback_reason}`);
  el.textContent = lines.join(" ｜ ");
}

async function parseErrorResponse(res) {
  const text = await res.text();
  try {
    const data = JSON.parse(text);
    if (data && typeof data.detail === "string") return data.detail;
    return text || `HTTP ${res.status}`;
  } catch {
    return text || `HTTP ${res.status}`;
  }
}

async function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function getProgressHint(job) {
  if (!job) return "等待任务状态...";
  if (job.status_text) return job.status_text;
  if (job.status === "queued") return "任务已创建，等待开始...";
  if (job.status === "running") {
    return "正在本地编码视频，首次生成可能需要几十秒到 2 分钟。";
  }
  if (job.status === "done") return "视频已生成完成。";
  if (job.status === "error") return `生成失败：${job.error || "未知错误"}`;
  return `当前状态：${job.status || "unknown"}`;
}

async function poll(jobId, onUpdate) {
  while (true) {
    const res = await fetch(`/api/jobs/${jobId}`, { cache: "no-store" });
    if (!res.ok) throw new Error(await parseErrorResponse(res));
    const job = await res.json();
    if (onUpdate) onUpdate(job);
    log(`status: ${job.status}${job.stage ? ` (${job.stage})` : ""}`);
    $("job_hint").textContent = getProgressHint(job);
    renderJobMeta(job);
    if (job.status === "running") {
      setGlobalStatus("生成中", "running");
      if (job.stage) setLoading(true, `正在处理：${job.stage}...`);
    }
    if (job.status === "done") return job;
    if (job.status === "error") throw new Error(job.error || "job failed");
    await sleep(1500);
  }
}

async function fetchJobs(limit = 20) {
  const res = await fetch(`/api/jobs?limit=${limit}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(await parseErrorResponse(res));
  const data = await res.json();
  return (data && data.jobs) || [];
}

async function fetchPlatformTemplates() {
  const res = await fetch('/api/platform-templates', { cache: 'no-store' });
  if (!res.ok) throw new Error(await parseErrorResponse(res));
  const data = await res.json();
  return (data && data.templates) || [];
}

let activeJobId = null;
let platformTemplates = [];

function renderJobs(jobs) {
  const list = $('job_list');
  if (!list) return;
  list.innerHTML = '';
  if (!jobs || jobs.length === 0) {
    list.innerHTML = '<div class="muted" style="font-size:12px;">暂无任务（点击右上角“生成视频”）</div>';
    return;
  }
  for (const j of jobs) {
    const el = document.createElement('div');
    const active = activeJobId && j.job_id === activeJobId;
    el.className = `job-item${active ? ' job-item--active' : ''}`;
    const st = j.status || 'unknown';
    const stage = j.stage ? `<div class="job-item__stage">${j.stage}</div>` : '';
    el.innerHTML = `
      <div class="job-item__top">
        <div class="job-item__id">${j.job_id}</div>
        <div class="job-item__status job-item__status--${st}">${st}</div>
      </div>
      ${stage}
      <div class="job-item__prompt">${(j.prompt || '').slice(0, 80) || '(no prompt)'}</div>
    `;
    el.addEventListener('click', () => {
      selectJob(j.job_id);
    });
    list.appendChild(el);
  }
}

async function refreshJobs() {
  const jobs = await fetchJobs(20);
  renderJobs(jobs);
  return jobs;
}

async function selectJob(jobId) {
  activeJobId = jobId;
  await refreshJobs();
  const res = await fetch(`/api/jobs/${jobId}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(await parseErrorResponse(res));
  const job = await res.json();
  $("job_hint").textContent = getProgressHint(job);
  renderJobMeta(job);

  const vid = $('video');
  if (job.status === 'done') {
    const url = `/api/jobs/${jobId}/result`;
    vid.src = url;
    vid.style.display = 'block';
    vid.load();
    setDownloadState(true, url);
    setGlobalStatus("生成完成", "done");
  } else {
    vid.removeAttribute('src');
    vid.load();
    vid.style.display = 'none';
    setDownloadState(false);
    if (job.status === 'running') {
      setGlobalStatus("生成中", "running");
    } else if (job.status === 'error') {
      setGlobalStatus("生成失败", "error");
    } else {
      setGlobalStatus("空闲中", "idle");
    }
  }
}

async function refreshAssets() {
  const res = await fetch('/api/assets?limit=20');
  if (!res.ok) throw new Error(await parseErrorResponse(res));
  const data = await res.json();
  const list = $('asset_list');
  if (!list) return;
  list.innerHTML = '';
  const assets = (data && data.assets) || [];
  if (assets.length === 0) {
    list.innerHTML = '<div class="muted" style="font-size:12px;">暂无视频素材（可拖拽到上方区域）</div>';
    return;
  }
  for (const a of assets) {
    const el = document.createElement('div');
    el.className = 'asset-item';
    const sizeMb = (a.size / (1024 * 1024)).toFixed(2);
    el.innerHTML = `
      <div class="asset-item__meta">
        <div class="asset-item__name">${a.filename}</div>
        <div class="asset-item__sub">
          <span class="asset-pill">${a.kind}</span>
          <span style="margin-left:8px;">${sizeMb} MB</span>
        </div>
      </div>
      <div class="asset-item__actions">
        <a class="btn" style="text-decoration:none;" href="/api/assets/${a.asset_id}" target="_blank">打开</a>
      </div>
    `;
    list.appendChild(el);
  }
}

async function uploadVideoFiles(files) {
  for (const f of files) {
    const fd = new FormData();
    fd.append('kind', 'video');
    fd.append('file', f);
    log(`uploading: ${f.name} ...`);
    const res = await fetch('/api/assets', { method: 'POST', body: fd });
    if (!res.ok) {
      throw new Error(await parseErrorResponse(res));
    }
  }
  await refreshAssets();
}

function setupDropzone() {
  const dz = $('dropzone');
  if (!dz) return;

  dz.addEventListener('dragover', (e) => {
    e.preventDefault();
    dz.classList.add('dragover');
  });
  dz.addEventListener('dragleave', () => dz.classList.remove('dragover'));
  dz.addEventListener('drop', async (e) => {
    e.preventDefault();
    dz.classList.remove('dragover');
    const files = e.dataTransfer && e.dataTransfer.files;
    if (!files || files.length === 0) return;
    const vids = Array.from(files).filter(f => f.type.startsWith('video/'));
    if (vids.length === 0) {
      alert('请拖拽视频文件（mp4/mov/mkv/webm）');
      return;
    }
    try {
      await uploadVideoFiles(vids);
      log('upload done');
    } catch (err) {
      const errorMsg = err && err.message ? err.message : String(err);
      console.error('Upload error:', err);
      logError('Video upload failed', { filename: vids[0].name, error: errorMsg });
      log('ERROR: ' + errorMsg);
      showErrorMessage(`上传失败：${errorMsg}`, err);
    }
  });
}

function renderTemplateSummary() {
  const select = $('template_id');
  const summary = $('template_summary');
  if (!select || !summary) return;
  const template = platformTemplates.find((item) => item.id === select.value);
  if (!template) {
    summary.textContent = '未找到模板说明。';
    return;
  }
  summary.textContent = `${template.name} ｜ ${template.platform} ｜ ${template.width}×${template.height} ｜ ${template.duration_s}s ｜ 封面 ${template.cover_width}×${template.cover_height} ｜ ${template.description}`;
}

async function initPlatformTemplates() {
  const select = $('template_id');
  const summary = $('template_summary');
  if (!select || !summary) return;

  platformTemplates = await fetchPlatformTemplates();
  select.innerHTML = '';
  for (const template of platformTemplates) {
    const option = document.createElement('option');
    option.value = template.id;
    option.textContent = template.name;
    select.appendChild(option);
  }
  if (!select.value && platformTemplates[0]) {
    select.value = platformTemplates[0].id;
  }
  renderTemplateSummary();
}

function syncBackendUI() {
  const backend = $('backend');
  const provider = $('provider');
  const note = $('advanced_note');
  if (!backend || !provider || !note) return;

  if (backend.value === 'local') {
    provider.disabled = true;
    note.textContent = '当前选择 local：直接走本地轻量渲染链路，不会调用云端 provider。平台模板会控制竖屏比例、时长和封面尺寸。';
  } else if (backend.value === 'cloud') {
    provider.disabled = false;
    note.textContent = '当前选择 cloud：会强制使用所选 provider；如果 provider 未配置，任务会直接失败。平台模板会同时写入输出规格。';
  } else {
    provider.disabled = false;
    note.textContent = '当前选择 auto：会优先尝试云端 provider，失败时自动回退到本地轻量渲染链路。平台模板会统一控制尺寸、时长和封面规格。';
  }
}

const videosInput = $('videos');
if (videosInput) {
  videosInput.addEventListener('change', async () => {
    const files = videosInput.files;
    if (!files || files.length === 0) return;
    try {
      await uploadVideoFiles(Array.from(files));
      log('upload done');
    } catch (err) {
      const errorMsg = err && err.message ? err.message : String(err);
      console.error('Upload error:', err);
      logError('File input upload failed', { count: files.length, error: errorMsg });
      log('ERROR: ' + errorMsg);
      showErrorMessage(`上传失败：${errorMsg}`, err);
    } finally {
      videosInput.value = '';
    }
  });
}

setupDropzone();
setDownloadState(false);
refreshAssets();
refreshJobs();
setGlobalStatus("空闲中", "idle");
initPlatformTemplates().catch((err) => {
  const errorMsg = err && err.message ? err.message : String(err);
  console.error('Template init error:', err);
  logError('Platform templates failed to load', { error: errorMsg });
  const summary = $('template_summary');
  if (summary) summary.textContent = '平台模板加载失败，请刷新页面重试。';
  log('ERROR: 平台模板加载失败 - ' + errorMsg);
  showErrorMessage('平台模板加载失败，请刷新页面后重试', err);
});
syncBackendUI();

$('backend')?.addEventListener('change', syncBackendUI);
$('template_id')?.addEventListener('change', renderTemplateSummary);

$("submit").addEventListener("click", async () => {
  try {
    $("log").textContent = "";
    const prompt = $("prompt").value;
    const storyboard = $("storyboard").value.trim();
    const backend = $("backend").value;
    const provider = $("provider").value;
    const templateId = $("template_id").value;
    const subtitles = $("subtitles").checked;
    const bgmFile = $("bgm").files && $("bgm").files[0];
    const bgmVolume = $("bgm_volume").value;
    const files = $("images").files;

    if (!files || files.length === 0) {
      alert("请至少上传一张宠物图片再生成视频。");
      return;
    }
    if (files.length > 12) {
      alert("单次最多上传 12 张图片。先做首轮验证，不要一次塞太多。");
      return;
    }

    const fd = new FormData();
    fd.append("prompt", prompt);
    fd.append("backend", backend);
    fd.append("provider", provider);
    fd.append("template_id", templateId);
    fd.append("subtitles", String(subtitles));
    fd.append("bgm_volume", String(bgmVolume));
    if (bgmFile) fd.append("bgm", bgmFile);
    if (storyboard) fd.append("storyboard_json", storyboard);
    for (const f of files) fd.append("images", f);

    setGlobalStatus("正在创建任务", "running");
    setDownloadState(false);
    renderJobMeta(null);
    $("job_hint").textContent = "正在提交任务，请稍等...";
    log("creating job...");
    setLoading(true, "正在上传图片...");
    
    // Use new upload with progress helper
    const { job_id } = await uploadWithProgress(fd);
    log(`job_id: ${job_id}`);

    activeJobId = job_id;
    await refreshJobs();
    setLoading(true, "正在排队等待渲染...");

    // Start progress simulation for rendering
    startProgressSimulation();

    log("rendering...");
    $("job_hint").textContent = "任务已提交，正在等待渲染反馈。";
    await poll(job_id, async (job) => {
      if (job && job.job_id) {
        activeJobId = job.job_id;
        await refreshJobs();
        // Update loading text with stage info
        if (job.stage) {
          setLoading(true, `正在处理：${job.stage}...`);
          // Sync simulation stage
          updateProgressStage(job.stage);
        }
      }
    });

    setLoading(false);
    stopProgressSimulation();
    await selectJob(job_id);
    log("done");
  } catch (e) {
    console.error(e);
    setGlobalStatus("生成失败", "error");
    log("ERROR: " + (e && e.message ? e.message : String(e)));
    $("job_hint").textContent = "生成失败，请查看下方日志。";
    showErrorMessage("生成失败：" + (e && e.message ? e.message : String(e)));
    setLoading(false);
    stopProgressSimulation();
  }
});

// --- Upload progress helper (XHR for upload % tracking) ---
function uploadWithProgress(fd, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/jobs", true);
    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable) {
        onProgress(Math.round((e.loaded / e.total) * 100), "正在上传图片...");
      }
    });
    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(xhr);
      } else {
        reject(new Error(xhr.responseText || `Upload failed (${xhr.status})`));
      }
    });
    xhr.addEventListener("error", () => reject(new Error("Network error during upload")));
    xhr.send(fd);
  });
}

// --- Generation progress tracking ---
const _genStageBounds = {
  preparing:    [0,   5,  "准备中"],
  rendering_cloud: [5,  75, "云端渲染中"],
  trying_cloud:    [75, 80, "尝试云端渲染"],
  rendering_local: [85, 95, "本地渲染中"],
  fallback_local:  [95, 98, "回退本地渲染"],
  done:            [100, 100, "完成"],
};

let _lastStageAt = 0;
let _lastProgress = 0;

function _stageProgress(stage, elapsedInStage) {
  const [lo, hi, label] = _genStageBounds[stage] || [0, 0, stage];
  const span = hi - lo;
  // Estimate 30s per stage if no external signal
  const stageTotal = 30000;
  const pct = span > 0 ? lo + Math.min(span, Math.round((elapsedInStage / stageTotal) * span)) : lo;
  return { pct: Math.min(pct, hi), label };
}

function _setGenProgress(stage, elapsed) {
  const { pct, label } = _stageProgress(stage, elapsed);
  const fill = document.getElementById("loading_progress_fill");
  const bar  = document.getElementById("loading_progress_bar");
  const etaEl = document.getElementById("loading_eta");
  if (fill) fill.style.width = pct + "%";
  if (bar)  bar.style.display = "block";

  // ETA: if we know elapsed and pct, estimate total and remaining
  if (elapsed > 5000 && pct > 1) {
    const totalEst = (elapsed / pct) * 100;
    const remaining = Math.max(0, Math.round((totalEst - elapsed) / 1000));
    if (etaEl) {
      etaEl.textContent = `预计剩余: ${remaining}s`;
    }
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

// --- Loading overlay helpers ---
function setLoading(isLoading, message) {
  const overlay  = document.getElementById("loading_overlay");
  const textEl   = document.getElementById("loading_text");
  const bar      = document.getElementById("loading_progress_bar");
  const fill     = document.getElementById("loading_progress_fill");
  const etaEl    = document.getElementById("loading_eta");
  const submitBtn = document.getElementById("submit");

  if (!overlay) return;

  if (isLoading) {
    overlay.style.display = "flex";
    if (textEl && message) textEl.textContent = message || "处理中...";
    if (bar)  bar.style.display = "none";
    if (fill) fill.style.width = "0%";
    if (etaEl) etaEl.textContent = "";
    if (submitBtn) submitBtn.disabled = true;
  } else {
    overlay.style.display = "none";
    if (bar)  bar.style.display = "none";
    if (etaEl) etaEl.textContent = "";
    if (submitBtn) submitBtn.disabled = false;
  }
}

$("submit").addEventListener("click", function() {
  this.disabled = true;
  setTimeout(() => this.disabled = false, 2000); // Basic debounce
});
