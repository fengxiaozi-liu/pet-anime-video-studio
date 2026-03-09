const $ = (id) => document.getElementById(id);

function log(msg) {
  const el = $("log");
  el.textContent += msg + "\n";
  el.scrollTop = el.scrollHeight;
}

async function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function poll(jobId) {
  while (true) {
    const res = await fetch(`/api/jobs/${jobId}`);
    const job = await res.json();
    log(`status: ${job.status}`);
    if (job.status === "done") return job;
    if (job.status === "error") throw new Error(job.error || "job failed");
    await sleep(1000);
  }
}

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
      alert("Please upload at least one image");
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

    log("rendering...");
    await poll(job_id);

    const url = `/api/jobs/${job_id}/result`;
    const vid = $("video");
    vid.src = url;
    vid.style.display = "block";
    vid.load();
    log("done");
  } catch (e) {
    console.error(e);
    log("ERROR: " + (e && e.message ? e.message : String(e)));
    alert("Failed: " + (e && e.message ? e.message : String(e)));
  }
});
