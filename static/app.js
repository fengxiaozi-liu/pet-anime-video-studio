const $ = (id) => document.getElementById(id);

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

async function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function getProgressHint(job) {
  if (!job) return "等待任务状态...";
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
    const job = await res.json();
    if (onUpdate) onUpdate(job);
    log(`status: ${job.status}`);
    $("job_hint").textContent = getProgressHint(job);
    if (job.status === "running") setGlobalStatus("本地编码中", "running");
    if (job.status === "done") return job;
    if (job.status === "error") throw new Error(job.error || "job failed");
    await sleep(1500);
  }
}

async function fetchJobs(limit = 20) {
  const res = await fetch(`/api/jobs?limit=${limit}`, { cache: 'no-store' });
  const data = await res.json();
  return (data && data.jobs) || [];
}

let activeJobId = null;

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
    el.innerHTML = `
      <div class="job-item__top">
        <div class="job-item__id">${j.job_id}</div>
        <div class="job-item__status job-item__status--${st}">${st}</div>
      </div>
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
  const job = await (await fetch(`/api/jobs/${jobId}`, { cache: 'no-store' })).json();
  $("job_hint").textContent = getProgressHint(job);
  if (job.status === 'done') {
    const url = `/api/jobs/${jobId}/result`;
    const vid = $('video');
    vid.src = url;
    vid.style.display = 'block';
    vid.load();
    setGlobalStatus("生成完成", "done");
  } else if (job.status === 'running') {
    setGlobalStatus("本地编码中", "running");
  } else if (job.status === 'error') {
    setGlobalStatus("生成失败", "error");
  } else {
    setGlobalStatus("空闲中", "idle");
  }
}

async function refreshAssets() {
  const res = await fetch('/api/assets?limit=20');
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
      const t = await res.text();
      throw new Error(t);
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
      console.error(err);
      log('ERROR: ' + (err && err.message ? err.message : String(err)));
      alert('上传失败：' + (err && err.message ? err.message : String(err)));
    }
  });
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
      console.error(err);
      log('ERROR: ' + (err && err.message ? err.message : String(err)));
      alert('上传失败：' + (err && err.message ? err.message : String(err)));
    } finally {
      videosInput.value = '';
    }
  });
}

setupDropzone();
refreshAssets();
refreshJobs();
setGlobalStatus("空闲中", "idle");

$("submit").addEventListener("click", async () => {
  try {
    $("log").textContent = "";
    const prompt = $("prompt").value;
    const storyboard = $("storyboard").value.trim();
    const backend = $("backend").value;
    const provider = $("provider").value;
    const subtitles = $("subtitles").checked;
    const bgmFile = $("bgm").files && $("bgm").files[0];
    const bgmVolume = $("bgm_volume").value;
    const files = $("images").files;

    if (!files || files.length === 0) {
      alert("请至少上传一张宠物图片再生成视频。");
      return;
    }

    const fd = new FormData();
    fd.append("prompt", prompt);
    fd.append("backend", backend);
    fd.append("provider", provider);
    fd.append("subtitles", String(subtitles));
    fd.append("bgm_volume", String(bgmVolume));
    if (bgmFile) fd.append("bgm", bgmFile);
    if (storyboard) fd.append("storyboard_json", storyboard);
    for (const f of files) fd.append("images", f);

    setGlobalStatus("正在创建任务", "running");
    $("job_hint").textContent = "正在提交任务，请稍等...";
    log("creating job...");
    const res = await fetch("/api/jobs", { method: "POST", body: fd });
    if (!res.ok) {
      const t = await res.text();
      throw new Error(t);
    }
    const { job_id } = await res.json();
    log(`job_id: ${job_id}`);

    activeJobId = job_id;
    await refreshJobs();

    log("rendering...");
    $("job_hint").textContent = "正在本地渲染，请不要关闭页面。";
    await poll(job_id, async (job) => {
      if (job && job.job_id) {
        activeJobId = job.job_id;
        await refreshJobs();
      }
    });

    await selectJob(job_id);
    log("done");
  } catch (e) {
    console.error(e);
    setGlobalStatus("生成失败", "error");
    log("ERROR: " + (e && e.message ? e.message : String(e)));
    $("job_hint").textContent = "生成失败，请查看下方日志。";
    alert("Failed: " + (e && e.message ? e.message : String(e)));
  }
});
