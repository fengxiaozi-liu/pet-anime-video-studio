const $ = (id) => document.getElementById(id);

function log(msg) {
  const el = $("log");
  el.textContent += msg + "\n";
  el.scrollTop = el.scrollHeight;
}

async function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function poll(jobId, onUpdate) {
  while (true) {
    const res = await fetch(`/api/jobs/${jobId}`);
    const job = await res.json();
    if (onUpdate) onUpdate(job);
    log(`status: ${job.status}`);
    if (job.status === "done") return job;
    if (job.status === "error") throw new Error(job.error || "job failed");
    await sleep(1000);
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
  if (job.status === 'done') {
    const url = `/api/jobs/${jobId}/result`;
    const vid = $('video');
    vid.src = url;
    vid.style.display = 'block';
    vid.load();
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
      alert("请至少上传一张图片（旧流程占位）。后续会改成‘视频素材’驱动。");
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

    log("creating job...");
    const res = await fetch("/api/jobs", { method: "POST", body: fd });
    if (!res.ok) {
      const t = await res.text();
      throw new Error(t);
    }
    const { job_id } = await res.json();
    log(`job_id: ${job_id}`);

    // refresh queue UI
    activeJobId = job_id;
    await refreshJobs();

    log("rendering...");
    await poll(job_id, async (job) => {
      // keep queue updated while running
      if (job && job.job_id) {
        activeJobId = job.job_id;
        await refreshJobs();
      }
    });

    await selectJob(job_id);
    log("done");
  } catch (e) {
    console.error(e);
    log("ERROR: " + (e && e.message ? e.message : String(e)));
    alert("Failed: " + (e && e.message ? e.message : String(e)));
  }
});
