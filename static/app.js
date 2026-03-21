const $ = (id) => document.getElementById(id);

const mockVisualStyles = [
  {
    id: "china-epic",
    name: "华丽古风",
    description: "盛世古风、服饰讲究、建筑恢弘、色彩华丽。",
    mediaClass: "resource-card__media--comic",
    styleText: "ornate ancient Chinese fantasy, cinematic lighting, rich costume details, grand architecture",
  },
  {
    id: "healing-anime",
    name: "治愈动漫",
    description: "柔和光线、日常感、清新空气和轻松氛围。",
    mediaClass: "",
    styleText: "healing anime, soft daylight, calm pacing, pastel color palette",
  },
  {
    id: "photo-film",
    name: "写实电影",
    description: "写实构图、电影感层次、镜头真实。",
    mediaClass: "resource-card__media--photo",
    styleText: "cinematic realism, film grain, dramatic composition, premium texture",
  },
  {
    id: "fantasy-xianxia",
    name: "仙侠古风",
    description: "人物飘逸、氛围梦幻、光晕和雾感明显。",
    mediaClass: "resource-card__media--fantasy",
    styleText: "xianxia fantasy, ethereal atmosphere, floating garments, misty light",
  },
];

const mockCharacters = {
  public: [
    { id: "guard", name: "城门守卫", note: "铠甲、长枪、威严站姿", mediaClass: "resource-card__media--photo" },
    { id: "merchant", name: "商贩", note: "热闹叫卖，带生活感", mediaClass: "resource-card__media--cute" },
    { id: "musician", name: "宫廷乐师", note: "适合宴乐场景", mediaClass: "resource-card__media--comic" },
    { id: "dancer", name: "舞姬", note: "舞动镜头中的焦点角色", mediaClass: "resource-card__media--fantasy" },
    { id: "scholar", name: "文人", note: "茶楼、诗会、对谈", mediaClass: "" },
  ],
  mine: [
    { id: "my-hero", name: "我的主角", note: "保留你的长期人设", mediaClass: "resource-card__media--photo" },
    { id: "my-pet", name: "我的宠物", note: "适合宠物故事长线角色", mediaClass: "resource-card__media--cute" },
  ],
};

const mockVoices = [
  { id: "voice-story-f", name: "曼波讲故事", type: "热门", tone: "温柔叙述 · 女声" },
  { id: "voice-broadcast-m", name: "自然纪录片", type: "热门", tone: "沉稳旁白 · 男声" },
  { id: "voice-host-f", name: "知性女声", type: "推荐", tone: "轻播音感 · 女声" },
  { id: "voice-youth-m", name: "清亮男声", type: "最新", tone: "年轻解说 · 男声" },
];

const mockMusic = [
  { id: "music-peace", name: "风（治愈纯音乐）", author: "治愈纯音乐", duration: "02:37", type: "推荐音乐" },
  { id: "music-ancient", name: "午后古巷轻松", author: "看见音乐", duration: "02:24", type: "推荐音乐" },
  { id: "music-warm", name: "欢快愉悦小调", author: "李闰驰", duration: "01:27", type: "热门" },
];

const state = {
  assistantPrompt: "",
  storySummary: "",
  storyText: "",
  scenes: [],
  visualStyleId: "china-epic",
  characterIds: [],
  voiceId: "voice-story-f",
  musicId: "music-peace",
  templateId: "",
  aspectRatio: "16:9",
  sceneType: "智能分镜，图片 4.0，Seedance 1.0",
  subtitles: true,
  bgmVolume: 0.25,
  provider: "",
  activeTab: "visual",
  characterScope: "public",
  voiceFilter: "热门",
  musicFilter: "推荐音乐",
  searches: {
    character: "",
    voice: "",
    music: "",
  },
  bgmFile: null,
  activeSceneIndex: 0,
  lastJobId: null,
};

let availableProviders = [];
let providerConfigs = [];
let platformTemplates = [];
let pollingTimer = null;

function page() {
  return document.body.dataset.page || "";
}

function pageIsStudio() {
  return page() === "studio";
}

function pageIsTasks() {
  return page() === "tasks";
}

function pageIsTaskDetail() {
  return page() === "task-detail";
}

function pageIsProviders() {
  return page() === "providers";
}

function activeJobId() {
  return document.body.dataset.jobId || "";
}

function styleById(id) {
  return mockVisualStyles.find((item) => item.id === id) || mockVisualStyles[0];
}

function selectedVoice() {
  return mockVoices.find((item) => item.id === state.voiceId) || null;
}

function selectedMusic() {
  return mockMusic.find((item) => item.id === state.musicId) || null;
}

function selectedProvider() {
  return availableProviders.find((item) => item.provider_code === state.provider) || null;
}

function charactersByIds(ids) {
  return [...mockCharacters.public, ...mockCharacters.mine].filter((item) => ids.includes(item.id));
}

function parseDate(ts) {
  if (!ts) return "未记录";
  const date = new Date(Number(ts) * 1000);
  if (Number.isNaN(date.getTime())) return "未记录";
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function statusLabel(status) {
  const map = {
    queued: "排队中",
    submitted: "已提交",
    running: "生成中",
    succeeded: "分镜完成",
    failed: "失败",
    composing: "合成中",
    done: "已完成",
    error: "错误",
  };
  return map[status] || status || "未知";
}

async function parseErrorResponse(res) {
  const text = await res.text();
  try {
    const data = JSON.parse(text);
    return data.detail || data.error || text || `HTTP ${res.status}`;
  } catch {
    return text || `HTTP ${res.status}`;
  }
}

async function fetchJson(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(await parseErrorResponse(res));
  if (res.status === 204) return {};
  return res.json();
}

async function fetchJobs(limit = 20) {
  const data = await fetchJson(`/api/jobs?limit=${limit}`, { cache: "no-store" });
  return data.jobs || [];
}

async function fetchJob(jobId) {
  return fetchJson(`/api/jobs/${jobId}`, { cache: "no-store" });
}

async function deleteJob(jobId) {
  return fetchJson(`/api/jobs/${jobId}`, { method: "DELETE" });
}

async function fetchPlatformTemplates() {
  const data = await fetchJson("/api/platform-templates", { cache: "no-store" });
  return data.templates || [];
}

async function fetchProviders() {
  const data = await fetchJson("/api/providers", { cache: "no-store" });
  return data.providers || [];
}

async function fetchProviderConfigs() {
  const data = await fetchJson("/api/provider-configs", { cache: "no-store" });
  return data.provider_configs || [];
}

async function updateProviderConfig(providerCode, payload) {
  return fetchJson(`/api/provider-configs/${providerCode}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

async function validateProviderConfig(providerCode, providerConfigJson) {
  return fetchJson(`/api/provider-configs/${providerCode}/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider_config_json: providerConfigJson }),
  });
}

function setLoading(visible, text = "处理中...") {
  const overlay = $("loading_overlay");
  const label = $("loading_text");
  if (!overlay) return;
  overlay.style.display = visible ? "flex" : "none";
  if (label) label.textContent = text;
  if (!visible) {
    const fill = $("loading_progress_fill");
    const bar = $("loading_progress_bar");
    const eta = $("loading_eta");
    if (fill) fill.style.width = "0%";
    if (bar) bar.style.display = "none";
    if (eta) eta.textContent = "";
  }
}

function showUploadProgress(pct, text) {
  const fill = $("loading_progress_fill");
  const bar = $("loading_progress_bar");
  const label = $("loading_text");
  const eta = $("loading_eta");
  if (bar) bar.style.display = "block";
  if (fill) fill.style.width = `${pct}%`;
  if (label) label.textContent = text;
  if (eta) eta.textContent = pct < 100 ? `上传中：${pct}%` : "";
}

function uploadWithProgress(formData) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/jobs", true);
    xhr.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable) {
        const pct = Math.round((event.loaded / event.total) * 100);
        showUploadProgress(pct, "正在提交生成任务...");
      }
    });
    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText));
        } catch {
          reject(new Error("服务端返回格式无效"));
        }
      } else {
        let detail = `请求失败 (${xhr.status})`;
        try {
          const payload = JSON.parse(xhr.responseText);
          detail = payload.detail || detail;
        } catch {}
        reject(new Error(detail));
      }
    });
    xhr.addEventListener("error", () => reject(new Error("网络异常")));
    xhr.send(formData);
  });
}

function setGlobalStatus(text, kind = "idle") {
  const el = $("global_status");
  if (!el) return;
  el.textContent = text;
  const map = {
    idle: { background: "rgba(255,255,255,0.74)", color: "#746353", borderColor: "rgba(72,52,33,0.12)" },
    running: { background: "rgba(220,234,229,0.96)", color: "#0e3f35", borderColor: "rgba(21,91,77,0.2)" },
    done: { background: "rgba(226,244,237,0.96)", color: "#25715b", borderColor: "rgba(37,113,91,0.22)" },
    error: { background: "rgba(252,236,234,0.96)", color: "#b44f4b", borderColor: "rgba(180,79,75,0.22)" },
  };
  const style = map[kind] || map.idle;
  Object.assign(el.style, style);
}

function setLinkState(id, enabled, href = "#") {
  const link = $(id);
  if (!link) return;
  link.href = href;
  link.setAttribute("aria-disabled", enabled ? "false" : "true");
  link.classList.toggle("is-disabled", !enabled);
}

function setDownloadState(enabled, href = "#") {
  setLinkState("download_result", enabled, href);
}

function buildDraftFromPrompt(prompt) {
  const clean = (prompt || "").trim() || "温暖的宠物奇遇故事";
  const style = styleById(state.visualStyleId);
  const leadNames = charactersByIds(state.characterIds).map((item) => item.name).join("、") || "主角";
  const scenes = [
    {
      title: "开场建立",
      prompt: `以“${clean}”为主题的开场镜头，先建立世界观和空间氛围，让观众迅速进入故事。`,
      subtitle: `故事从这里开始：${clean}`,
      duration_s: 4,
      characterIds: state.characterIds.length ? [...state.characterIds] : ["my-pet"],
    },
    {
      title: "角色登场",
      prompt: `主角 ${leadNames} 正式进入画面，镜头更贴近人物表情和动作，建立情绪联系。`,
      subtitle: `${leadNames} 的故事逐渐展开。`,
      duration_s: 4,
      characterIds: state.characterIds.length ? [...state.characterIds] : ["guard"],
    },
    {
      title: "情绪推进",
      prompt: `通过更丰富的环境和动作细节推进故事，强化“${style.name}”的视觉氛围。`,
      subtitle: `情绪来到最饱满的一段。`,
      duration_s: 4,
      characterIds: state.characterIds.length ? [...state.characterIds] : ["merchant"],
    },
    {
      title: "收束结尾",
      prompt: `回到主角视角，用一个有余韵的镜头结束，形成完整闭环。`,
      subtitle: "故事在温柔的尾声里结束。",
      duration_s: 4,
      characterIds: state.characterIds.length ? [...state.characterIds] : ["my-pet"],
    },
  ];
  const summary = `这个视频以“${clean}”为主线，通过 ${scenes.length} 个分镜推进故事节奏。画面建议采用“${style.name}”风格，并以 ${leadNames} 为核心完成一支可直接提交生成的视频草稿。`;
  const storyText = scenes.map((scene, index) => `分镜${index + 1}：${scene.title}\n${scene.prompt}\n字幕：${scene.subtitle}`).join("\n\n");
  return { summary, storyText, scenes };
}

function renderAssistantThread() {
  const thread = $("assistant_thread");
  if (!thread) return;
  if (!state.assistantPrompt) {
    thread.innerHTML = '<div class="chat-bubble chat-bubble--assistant">Hi，今天想做什么视频？把主题、情绪、角色关系或者镜头氛围告诉我，我会先给你一版故事和分镜草稿。</div>';
    return;
  }
  thread.innerHTML = `
    <div class="chat-bubble chat-bubble--user">${state.assistantPrompt}</div>
    <div class="chat-bubble chat-bubble--assistant">视频策划方案已经备好。你可以在中间编辑故事和分镜，再从右侧选择画面、角色、配音和音乐。</div>
  `;
}

function renderAssistantPlan() {
  const plan = $("assistant_plan");
  if (!plan) return;
  if (!state.storySummary) {
    plan.innerHTML = `
      <div class="assistant-card">
        <h3>等待生成策划案</h3>
        <div class="assistant-card__summary">先输入一个主题，我会生成内容概览、故事文本和 4 段可编辑分镜草稿。</div>
      </div>
    `;
    return;
  }
  plan.innerHTML = `
    <div class="assistant-card">
      <h3>策划案已生成</h3>
      <div class="assistant-card__meta">${styleById(state.visualStyleId).name} · ${state.scenes.length} 个分镜 · ${state.aspectRatio}</div>
      <div class="assistant-card__summary">${state.storySummary}</div>
    </div>
  `;
}

function renderStoryEditors() {
  if ($("story_summary")) $("story_summary").value = state.storySummary;
  if ($("story_text")) $("story_text").value = state.storyText;
}

function renderSceneSummary() {
  const summary = $("scene_summary");
  if (!summary) return;
  if (!state.scenes.length) {
    summary.textContent = "还没有分镜，先让助手生成一版草稿。";
    return;
  }
  const totalDuration = state.scenes.reduce((sum, scene) => sum + Number(scene.duration_s || 0), 0);
  summary.textContent = `当前共有 ${state.scenes.length} 个分镜，总时长约 ${totalDuration.toFixed(1)} 秒。`;
}

function renderSceneList() {
  const list = $("scene_list");
  if (!list) return;
  if (!state.scenes.length) {
    list.innerHTML = '<div class="scene-card"><div class="field-hint">这里会展示分镜卡片。你可以先在左侧生成一版故事，也可以直接新增分镜手动编辑。</div></div>';
    renderSceneSummary();
    return;
  }
  list.innerHTML = state.scenes.map((scene, index) => {
    const roleTags = charactersByIds(scene.characterIds || []).map((item) => `<span class="tag">${item.name}</span>`).join("");
    return `
      <article class="scene-card ${state.activeSceneIndex === index ? "is-active" : ""}" data-scene-index="${index}">
        <div class="scene-card__head">
          <div class="scene-card__title">
            <strong>分镜 ${index + 1} · ${scene.title || "未命名分镜"}</strong>
            <span>${state.sceneType}</span>
          </div>
          <div class="scene-card__actions">
            <button class="icon-btn" data-action="move-up" data-scene-index="${index}" title="上移">↑</button>
            <button class="icon-btn" data-action="move-down" data-scene-index="${index}" title="下移">↓</button>
            <button class="icon-btn" data-action="delete" data-scene-index="${index}" title="删除">×</button>
          </div>
        </div>
        <div class="scene-grid">
          <div>
            <label>画面描述</label>
            <textarea data-field="prompt" data-scene-index="${index}" rows="4">${scene.prompt || ""}</textarea>
          </div>
          <div>
            <label>时长（秒）</label>
            <input data-field="duration_s" data-scene-index="${index}" type="number" min="0.5" max="60" step="0.5" value="${scene.duration_s}" />
            <label style="margin-top:12px;">标题</label>
            <input data-field="title" data-scene-index="${index}" type="text" value="${scene.title || ""}" />
          </div>
        </div>
        <div style="margin-top:12px;">
          <label>字幕</label>
          <textarea data-field="subtitle" data-scene-index="${index}" rows="2">${scene.subtitle || ""}</textarea>
        </div>
        <div class="scene-footer">${roleTags || '<span class="field-hint">当前分镜还没有绑定角色，可从右侧角色库应用。</span>'}</div>
      </article>
    `;
  }).join("");
  renderSceneSummary();
}

function renderProviderSelect() {
  const select = $("studio_provider");
  if (!select) return;
  if (!availableProviders.length) {
    select.innerHTML = '<option value="">暂无可用 Provider</option>';
    state.provider = "";
    return;
  }
  select.innerHTML = availableProviders.map((item) => `<option value="${item.provider_code}">${item.display_name}</option>`).join("");
  if (!state.provider || !availableProviders.some((item) => item.provider_code === state.provider)) {
    state.provider = availableProviders[0].provider_code;
  }
  select.value = state.provider;
}

function renderResourceNote() {
  const note = $("resource_note");
  if (!note) return;
  const voice = selectedVoice();
  const music = selectedMusic();
  const provider = selectedProvider();
  note.textContent = `已选画风：${styleById(state.visualStyleId).name}；角色：${state.characterIds.length} 个；提供商：${provider ? provider.display_name : "未配置"}；配音：${voice ? voice.name : "未选"}；音乐：${music ? music.name : "未选"}。`;
}

function renderVisualTab() {
  return `
    <div class="panel-section">
      <h3>素材</h3>
      <div class="resource-grid">
        ${mockVisualStyles.map((item) => `
          <article class="resource-card ${state.visualStyleId === item.id ? "is-selected" : ""}" data-style-id="${item.id}">
            <div class="resource-card__media ${item.mediaClass || ""}"></div>
            <strong>${item.name}</strong>
            <span>${item.description}</span>
          </article>
        `).join("")}
      </div>
    </div>
    <div class="panel-section">
      <h3>画面设置</h3>
      <div class="setting-card">
        <label for="aspect_ratio">视频比例</label>
        <select id="aspect_ratio">
          <option value="16:9" ${state.aspectRatio === "16:9" ? "selected" : ""}>16:9</option>
          <option value="9:16" ${state.aspectRatio === "9:16" ? "selected" : ""}>9:16</option>
          <option value="1:1" ${state.aspectRatio === "1:1" ? "selected" : ""}>1:1</option>
          <option value="4:3" ${state.aspectRatio === "4:3" ? "selected" : ""}>4:3</option>
        </select>
      </div>
      <div class="setting-card" style="margin-top:12px;">
        <label for="template_id">平台模板</label>
        <select id="template_id">
          ${platformTemplates.map((item) => `<option value="${item.id}" ${item.id === state.templateId ? "selected" : ""}>${item.name}</option>`).join("")}
        </select>
      </div>
      <label class="setting-toggle" style="margin-top:12px;">
        <input id="subtitles" type="checkbox" ${state.subtitles ? "checked" : ""} />
        <span>按原文匹配字幕</span>
      </label>
    </div>
  `;
}

function renderCharacterTab() {
  const scopeList = mockCharacters[state.characterScope];
  const query = state.searches.character.trim().toLowerCase();
  const list = scopeList.filter((item) => !query || `${item.name}${item.note}`.toLowerCase().includes(query));
  return `
    <div class="panel-section">
      <h3>角色选择列表</h3>
      <div class="segment-control">
        <button class="${state.characterScope === "public" ? "is-active" : ""}" data-character-scope="public">公共角色</button>
        <button class="${state.characterScope === "mine" ? "is-active" : ""}" data-character-scope="mine">我的角色</button>
      </div>
    </div>
    <div class="panel-section">
      <input class="search-input" id="character_search" placeholder="搜索角色名称" value="${state.searches.character}" />
    </div>
    <div class="panel-section">
      <div class="character-grid">
        ${list.map((item) => `
          <article class="character-card ${state.characterIds.includes(item.id) ? "is-selected" : ""}" data-character-id="${item.id}">
            <div class="character-card__media ${item.mediaClass || ""}"></div>
            <strong>${item.name}</strong>
            <span>${item.note}</span>
          </article>
        `).join("")}
      </div>
    </div>
  `;
}

function renderVoiceTab() {
  const query = state.searches.voice.trim().toLowerCase();
  const list = mockVoices.filter((item) => {
    const matchesFilter = state.voiceFilter === "全部" || item.type === state.voiceFilter;
    const matchesQuery = !query || `${item.name}${item.tone}`.toLowerCase().includes(query);
    return matchesFilter && matchesQuery;
  });
  return `
    <div class="panel-section">
      <h3>配音库</h3>
      <input class="search-input" id="voice_search" placeholder="搜索音色名称" value="${state.searches.voice}" />
    </div>
    <div class="panel-section">
      <div class="filter-row">
        ${["热门", "最新", "推荐", "全部"].map((filter) => `<button class="filter-chip ${state.voiceFilter === filter ? "is-active" : ""}" data-voice-filter="${filter}">${filter}</button>`).join("")}
      </div>
    </div>
    <div class="voice-list">
      ${list.map((item) => `
        <article class="voice-item ${state.voiceId === item.id ? "is-selected" : ""}" data-voice-id="${item.id}">
          <div class="voice-item__meta">
            <strong>${item.name}</strong>
            <span>${item.tone}</span>
          </div>
          <span>${item.type}</span>
        </article>
      `).join("")}
    </div>
  `;
}

function renderMusicTab() {
  const query = state.searches.music.trim().toLowerCase();
  const list = mockMusic.filter((item) => {
    const matchesFilter = state.musicFilter === "全部" || item.type === state.musicFilter;
    const matchesQuery = !query || `${item.name}${item.author}`.toLowerCase().includes(query);
    return matchesFilter && matchesQuery;
  });
  return `
    <div class="panel-section">
      <h3>音乐素材库</h3>
      <input class="search-input" id="music_search" placeholder="搜索歌曲名称 / 歌手" value="${state.searches.music}" />
    </div>
    <div class="panel-section">
      <div class="setting-card">
        <label for="bgm">本地 BGM 文件</label>
        <input id="bgm" type="file" accept="audio/*" />
      </div>
      <div class="setting-card" style="margin-top:10px;">
        <label for="bgm_volume">背景音乐音量</label>
        <input id="bgm_volume" type="number" value="${state.bgmVolume}" step="0.05" min="0" max="2" />
      </div>
    </div>
    <div class="panel-section">
      <div class="filter-row">
        ${["推荐音乐", "热门", "全部"].map((filter) => `<button class="filter-chip ${state.musicFilter === filter ? "is-active" : ""}" data-music-filter="${filter}">${filter}</button>`).join("")}
      </div>
    </div>
    <div class="music-list">
      ${list.map((item) => `
        <article class="music-item ${state.musicId === item.id ? "is-selected" : ""}" data-music-id="${item.id}">
          <div class="music-item__meta">
            <strong>${item.name}</strong>
            <span>${item.author} · ${item.duration}</span>
          </div>
          <span>${item.type}</span>
        </article>
      `).join("")}
    </div>
  `;
}

function renderResourcePanel() {
  const panel = $("resource_panel");
  if (!panel) return;
  const renderers = {
    visual: renderVisualTab,
    character: renderCharacterTab,
    voice: renderVoiceTab,
    music: renderMusicTab,
  };
  panel.innerHTML = renderers[state.activeTab]();
  document.querySelectorAll(".resource-tab").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.tab === state.activeTab);
  });
  renderResourceNote();
}

function renderAll() {
  renderAssistantThread();
  renderAssistantPlan();
  renderStoryEditors();
  renderSceneList();
  renderProviderSelect();
  renderResourcePanel();
}

function log(msg) {
  const el = $("log");
  if (!el) return;
  el.textContent += `${msg}\n`;
  el.scrollTop = el.scrollHeight;
}

function generateDraft() {
  const prompt = $("assistant_prompt")?.value.trim() || "";
  if (!prompt) {
    window.alert("先输入你想创作的视频主题。");
    return;
  }
  state.assistantPrompt = prompt;
  const draft = buildDraftFromPrompt(prompt);
  state.storySummary = draft.summary;
  state.storyText = draft.storyText;
  state.scenes = draft.scenes;
  state.activeSceneIndex = 0;
  renderAll();
}

function addScene() {
  state.scenes.push({
    title: `新增分镜 ${state.scenes.length + 1}`,
    prompt: "描述这一镜头的画面、镜头语言和环境细节。",
    subtitle: "这里是对应字幕。",
    duration_s: 4,
    characterIds: [...state.characterIds],
  });
  state.activeSceneIndex = state.scenes.length - 1;
  renderAll();
}

function removeScene(index) {
  state.scenes.splice(index, 1);
  state.activeSceneIndex = Math.max(0, Math.min(state.activeSceneIndex, state.scenes.length - 1));
  renderAll();
}

function moveScene(index, offset) {
  const next = index + offset;
  if (next < 0 || next >= state.scenes.length) return;
  const [scene] = state.scenes.splice(index, 1);
  state.scenes.splice(next, 0, scene);
  state.activeSceneIndex = next;
  renderAll();
}

function toggleCharacterSelection(id) {
  if (state.characterIds.includes(id)) {
    state.characterIds = state.characterIds.filter((item) => item !== id);
  } else {
    state.characterIds = [...state.characterIds, id];
  }
  const scene = state.scenes[state.activeSceneIndex];
  if (scene) {
    if (scene.characterIds.includes(id)) {
      scene.characterIds = scene.characterIds.filter((item) => item !== id);
    } else {
      scene.characterIds = [...scene.characterIds, id];
    }
  }
}

function buildStoryboardPayload() {
  const template = platformTemplates.find((item) => item.id === state.templateId) || null;
  const aspectMap = {
    "16:9": { width: 1280, height: 720 },
    "9:16": { width: 720, height: 1280 },
    "1:1": { width: 1080, height: 1080 },
    "4:3": { width: 1280, height: 960 },
  };
  const aspect = aspectMap[state.aspectRatio] || aspectMap["16:9"];
  const style = styleById(state.visualStyleId);
  return {
    template_id: state.templateId || null,
    width: template ? template.width : aspect.width,
    height: template ? template.height : aspect.height,
    duration_s: state.scenes.reduce((sum, scene) => sum + Number(scene.duration_s || 0), 0) || (template ? template.duration_s : 15),
    style: `${style.styleText}; scene type: ${state.sceneType}; selected voice: ${selectedVoice()?.name || "none"}; selected music: ${selectedMusic()?.name || "none"}`,
    subtitles: state.subtitles,
    bgm_volume: Number(state.bgmVolume),
    scenes: state.scenes.map((scene) => ({
      duration_s: Number(scene.duration_s || 4),
      prompt: scene.prompt || "",
      subtitle: scene.subtitle || "",
      title: scene.title || "",
    })),
  };
}

function updateJobMeta(job) {
  const meta = $("job_meta");
  if (!meta) return;
  if (!job) {
    meta.textContent = "";
    return;
  }
  const counts = job.scene_status_counts || {};
  const parts = [
    `父任务状态：${statusLabel(job.status)}`,
    `分镜：${job.scene_count || 0}`,
    `成功：${counts.succeeded || 0}`,
    `运行：${counts.running || 0}`,
    `提交：${counts.submitted || 0}`,
    `失败：${counts.failed || 0}`,
  ];
  meta.textContent = parts.join(" ｜ ");
}

async function watchJob(jobId) {
  if (pollingTimer) window.clearInterval(pollingTimer);
  const hint = $("job_hint");
  const tick = async () => {
    try {
      const job = await fetchJob(jobId);
      updateJobMeta(job);
      if (hint) hint.textContent = `当前任务：${statusLabel(job.status)}${job.stage ? ` · ${job.stage}` : ""}`;
      log(`status: ${job.status}${job.stage ? ` (${job.stage})` : ""}`);
      if (job.status === "done") {
        setLoading(false);
        setGlobalStatus("生成完成", "done");
        setDownloadState(true, `/api/jobs/${jobId}/result`);
        if (hint) hint.textContent = "视频已生成完成，可以下载结果。";
        window.clearInterval(pollingTimer);
        pollingTimer = null;
      }
      if (job.status === "failed" || job.status === "error") {
        setLoading(false);
        setGlobalStatus("生成失败", "error");
        if (hint) hint.textContent = `生成失败：${job.error || "未知错误"}`;
        window.clearInterval(pollingTimer);
        pollingTimer = null;
      }
    } catch (error) {
      setLoading(false);
      setGlobalStatus("生成失败", "error");
      if (hint) hint.textContent = `任务查询失败：${error.message}`;
      window.clearInterval(pollingTimer);
      pollingTimer = null;
    }
  };
  await tick();
  pollingTimer = window.setInterval(tick, 2000);
}

async function submitJob() {
  state.storySummary = $("story_summary")?.value || state.storySummary;
  state.storyText = $("story_text")?.value || state.storyText;
  if (!state.provider) {
    window.alert("当前没有可用 Provider，请先到“提供商配置”页完成配置并启用。");
    return;
  }
  if (!state.scenes.length) {
    window.alert("先生成或新增至少一个分镜。");
    return;
  }
  const formData = new FormData();
  formData.append("prompt", state.assistantPrompt || state.storySummary || state.storyText || "Video storyboard draft");
  formData.append("backend", "cloud");
  formData.append("provider", state.provider);
  formData.append("template_id", state.templateId || "");
  formData.append("subtitles", String(state.subtitles));
  formData.append("bgm_volume", String(state.bgmVolume));
  formData.append("storyboard_json", JSON.stringify(buildStoryboardPayload()));
  if (state.bgmFile) formData.append("bgm", state.bgmFile);

  setLoading(true, "正在创建生成任务...");
  setGlobalStatus("正在创建任务", "running");
  setDownloadState(false);
  updateJobMeta(null);
  if ($("job_hint")) $("job_hint").textContent = "正在提交任务，请稍等...";
  if ($("log")) $("log").textContent = "";

  try {
    const response = await uploadWithProgress(formData);
    state.lastJobId = response.job_id;
    log(`job_id: ${response.job_id}`);
    setGlobalStatus("分镜生成中", "running");
    await watchJob(response.job_id);
  } catch (error) {
    setLoading(false);
    setGlobalStatus("生成失败", "error");
    if ($("job_hint")) $("job_hint").textContent = `生成失败：${error.message}`;
    log(`ERROR: ${error.message}`);
    window.alert(`生成失败：${error.message}`);
  }
}

function attachStudioEvents() {
  $("assistant_generate")?.addEventListener("click", generateDraft);
  $("add_scene")?.addEventListener("click", addScene);
  $("submit")?.addEventListener("click", submitJob);

  document.addEventListener("click", (event) => {
    if (!pageIsStudio()) return;
    const target = event.target.closest("[data-tab], [data-style-id], [data-character-id], [data-character-scope], [data-voice-id], [data-music-id], [data-voice-filter], [data-music-filter], [data-action], .scene-card");
    if (!target) return;
    if (target.dataset.tab) {
      state.activeTab = target.dataset.tab;
      renderResourcePanel();
      return;
    }
    if (target.dataset.styleId) {
      state.visualStyleId = target.dataset.styleId;
      renderAll();
      return;
    }
    if (target.dataset.characterScope) {
      state.characterScope = target.dataset.characterScope;
      renderResourcePanel();
      return;
    }
    if (target.dataset.characterId) {
      toggleCharacterSelection(target.dataset.characterId);
      renderAll();
      return;
    }
    if (target.dataset.voiceId) {
      state.voiceId = target.dataset.voiceId;
      renderResourceNote();
      renderResourcePanel();
      return;
    }
    if (target.dataset.musicId) {
      state.musicId = target.dataset.musicId;
      renderResourceNote();
      renderResourcePanel();
      return;
    }
    if (target.dataset.voiceFilter) {
      state.voiceFilter = target.dataset.voiceFilter;
      renderResourcePanel();
      return;
    }
    if (target.dataset.musicFilter) {
      state.musicFilter = target.dataset.musicFilter;
      renderResourcePanel();
      return;
    }
    if (target.dataset.action) {
      const index = Number(target.dataset.sceneIndex);
      if (target.dataset.action === "delete") removeScene(index);
      if (target.dataset.action === "move-up") moveScene(index, -1);
      if (target.dataset.action === "move-down") moveScene(index, 1);
      return;
    }
    const sceneCard = target.closest(".scene-card");
    if (sceneCard && sceneCard.dataset.sceneIndex) {
      state.activeSceneIndex = Number(sceneCard.dataset.sceneIndex);
      renderSceneList();
    }
  });

  document.addEventListener("input", (event) => {
    if (!pageIsStudio()) return;
    const sceneIndex = event.target.dataset?.sceneIndex;
    const field = event.target.dataset?.field;
    if (sceneIndex !== undefined && field) {
      const scene = state.scenes[Number(sceneIndex)];
      if (!scene) return;
      scene[field] = field === "duration_s" ? Number(event.target.value) : event.target.value;
      renderSceneSummary();
      return;
    }
    if (event.target.id === "story_summary") state.storySummary = event.target.value;
    if (event.target.id === "story_text") state.storyText = event.target.value;
    if (event.target.id === "character_search") {
      state.searches.character = event.target.value;
      renderResourcePanel();
    }
    if (event.target.id === "voice_search") {
      state.searches.voice = event.target.value;
      renderResourcePanel();
    }
    if (event.target.id === "music_search") {
      state.searches.music = event.target.value;
      renderResourcePanel();
    }
    if (event.target.id === "bgm_volume") state.bgmVolume = Number(event.target.value);
  });

  document.addEventListener("change", (event) => {
    if (!pageIsStudio()) return;
    if (event.target.id === "studio_provider") {
      state.provider = event.target.value;
      renderResourceNote();
    }
    if (event.target.id === "aspect_ratio") {
      state.aspectRatio = event.target.value;
    }
    if (event.target.id === "template_id") {
      state.templateId = event.target.value;
    }
    if (event.target.id === "subtitles") {
      state.subtitles = event.target.checked;
    }
    if (event.target.id === "bgm") {
      state.bgmFile = event.target.files?.[0] || null;
    }
  });
}

async function initStudio() {
  setGlobalStatus("初始化中", "idle");
  try {
    [platformTemplates, availableProviders, providerConfigs] = await Promise.all([
      fetchPlatformTemplates(),
      fetchProviders(),
      fetchProviderConfigs(),
    ]);
    state.templateId = platformTemplates[0]?.id || "";
    state.provider = availableProviders[0]?.provider_code || "";
    renderAll();
    attachStudioEvents();
    if (!availableProviders.length) {
      setGlobalStatus("暂无可用 Provider", "error");
      if ($("job_hint")) $("job_hint").textContent = "当前没有已启用且校验通过的 Provider，请先到“提供商配置”页完成配置。";
    } else {
      setGlobalStatus("空闲中", "idle");
    }
  } catch (error) {
    setGlobalStatus("初始化失败", "error");
    if ($("job_hint")) $("job_hint").textContent = `初始化失败：${error.message}`;
  }
}

function jobShortId(job) {
  const id = job.job_id || "";
  return id ? `${id.slice(0, 8)}...` : "未知任务";
}

function renderTasksList(jobs) {
  const list = $("tasks_list");
  if (!list) return;
  if (!jobs.length) {
    list.innerHTML = `
      <div class="tasks-empty">
        <h3>暂无任务记录</h3>
        <p>任务会在工作台点击“生成视频”后自动出现在这里。</p>
        <a class="btn btn--secondary" href="/studio">进入工作台</a>
      </div>
    `;
    return;
  }
  list.innerHTML = jobs.map((job) => {
    const cover = job.status === "done"
      ? `<img class="task-card__cover" src="/api/jobs/${job.job_id}/export/cover" alt="任务封面" loading="lazy" />`
      : `<div class="task-card__placeholder">${statusLabel(job.status)}</div>`;
    const counts = job.scene_status_counts || {};
    return `
      <a class="task-card" href="/tasks/${job.job_id}">
        <div class="task-card__media">${cover}</div>
        <div class="task-card__body">
          <div class="task-card__top">
            <span class="task-card__id">${jobShortId(job)}</span>
            <span class="task-card__badge task-card__badge--${job.status}">${statusLabel(job.status)}</span>
          </div>
          <strong>${job.prompt || "未填写提示词"}</strong>
          <p>${job.status_text || job.stage || "暂无状态说明"}</p>
          <div class="task-card__meta">
            <span>${job.provider_code || "未指定提供商"}</span>
            <span>${job.template_name || "未指定模板"}</span>
            <span>分镜 ${job.scene_count || 0}</span>
            <span>成功 ${counts.succeeded || 0}</span>
            <span>${parseDate(job.created_at)}</span>
          </div>
        </div>
      </a>
    `;
  }).join("");
}

async function initTasksPage() {
  const list = $("tasks_list");
  const refresh = $("tasks_refresh");
  if (!list) return;
  const load = async () => {
    list.innerHTML = '<div class="tasks-loading">正在加载任务列表。</div>';
    try {
      const jobs = await fetchJobs(30);
      renderTasksList(jobs);
    } catch (error) {
      list.innerHTML = `
        <div class="tasks-empty">
          <h3>任务列表加载失败</h3>
          <p>${error.message}</p>
          <button class="btn btn--secondary" id="tasks_retry" type="button">重试</button>
        </div>
      `;
      $("tasks_retry")?.addEventListener("click", load, { once: true });
    }
  };
  refresh?.addEventListener("click", load);
  await load();
}

function taskMetric(label, value) {
  return `<div class="task-meta-item"><span>${label}</span><strong>${value || "未记录"}</strong></div>`;
}

function renderTaskScenes(job) {
  const list = $("task_scenes_list");
  if (!list) return;
  const scenes = job.scene_jobs || [];
  if (!scenes.length) {
    list.innerHTML = '<div class="tasks-empty"><h3>暂无分镜任务</h3><p>当前父任务下还没有创建任何分镜子任务。</p></div>';
    return;
  }
  list.innerHTML = scenes.map((scene) => {
    const payload = scene.scene_payload || {};
    return `
      <article class="task-scene-card">
        <div class="task-scene-card__head">
          <strong>分镜 ${scene.scene_index + 1}</strong>
          <span class="task-card__badge task-card__badge--${scene.normalized_status}">${statusLabel(scene.normalized_status)}</span>
        </div>
        <p>${payload.prompt || "未记录分镜描述"}</p>
        <div class="task-card__meta">
          <span>Provider：${scene.provider_code}</span>
          <span>厂商任务：${scene.provider_task_id || "未提交"}</span>
          <span>厂商状态：${scene.provider_status || "未记录"}</span>
          <span>轮询次数：${scene.poll_attempts || 0}</span>
        </div>
        ${scene.result_video_url ? `<a class="btn btn--ghost" href="${scene.result_video_url}" target="_blank" rel="noreferrer">查看分镜结果</a>` : ""}
      </article>
    `;
  }).join("");
}

function renderTaskDetail(job) {
  if ($("task_detail_title")) $("task_detail_title").textContent = `任务 ${jobShortId(job)}`;
  if ($("task_detail_subtitle")) $("task_detail_subtitle").textContent = job.prompt || "未填写提示词";
  if ($("task_detail_status")) $("task_detail_status").textContent = statusLabel(job.status);
  if ($("task_status_text")) $("task_status_text").textContent = job.status_text || job.stage || "暂无状态信息";
  if ($("task_action_error")) {
    $("task_action_error").hidden = true;
    $("task_action_error").textContent = "";
  }

  const storyboard = job.storyboard || {};
  if ($("task_meta_grid")) {
    $("task_meta_grid").innerHTML = [
      taskMetric("状态", statusLabel(job.status)),
      taskMetric("阶段", job.stage || "未记录"),
      taskMetric("提供商", job.provider_code || "未记录"),
      taskMetric("模板", job.template_name || "未记录"),
      taskMetric("分镜数", String(job.scene_count || 0)),
      taskMetric("时长", storyboard.duration_s ? `${storyboard.duration_s}s` : "未记录"),
      taskMetric("分辨率", storyboard.width && storyboard.height ? `${storyboard.width}×${storyboard.height}` : "未记录"),
      taskMetric("创建时间", parseDate(job.created_at)),
      taskMetric("更新时间", parseDate(job.updated_at)),
    ].join("");
  }

  const done = job.status === "done";
  setLinkState("task_download_video", done, done ? `/api/jobs/${job.job_id}/result` : "#");
  setLinkState("task_download_cover", done, done ? `/api/jobs/${job.job_id}/export/cover` : "#");
  setLinkState("task_download_package", done, done ? `/api/jobs/${job.job_id}/export/package` : "#");

  const video = $("task_video");
  const placeholder = $("task_placeholder");
  if (video && placeholder) {
    if (done) {
      const src = `/api/jobs/${job.job_id}/result`;
      if (video.dataset.src !== src) {
        video.src = src;
        video.dataset.src = src;
        video.load();
      }
      video.style.display = "block";
      placeholder.style.display = "none";
    } else {
      video.removeAttribute("src");
      video.dataset.src = "";
      video.style.display = "none";
      placeholder.style.display = "grid";
      placeholder.textContent = job.status === "failed" || job.status === "error"
        ? `任务失败：${job.error || "未知错误"}`
        : "视频正在生成中，完成后会自动出现在这里。";
    }
  }
  renderTaskScenes(job);
}

async function initTaskDetailPage() {
  const jobId = activeJobId();
  if (!jobId) return;
  const deleteButton = $("task_delete");
  const actionError = $("task_action_error");

  const load = async () => {
    const job = await fetchJob(jobId);
    renderTaskDetail(job);
    return job;
  };

  deleteButton?.addEventListener("click", async () => {
    if (!window.confirm("确认删除这个任务吗？删除后无法恢复。")) return;
    if (actionError) {
      actionError.hidden = true;
      actionError.textContent = "";
    }
    deleteButton.disabled = true;
    deleteButton.textContent = "删除中...";
    try {
      if (pollingTimer) {
        window.clearInterval(pollingTimer);
        pollingTimer = null;
      }
      await deleteJob(jobId);
      window.location.href = "/tasks";
    } catch (error) {
      deleteButton.disabled = false;
      deleteButton.textContent = "删除任务";
      if (actionError) {
        actionError.hidden = false;
        actionError.textContent = `删除失败：${error.message}`;
      }
    }
  });

  try {
    const initial = await load();
    if (initial.status === "done" || initial.status === "failed" || initial.status === "error") return;
    pollingTimer = window.setInterval(async () => {
      try {
        const job = await load();
        if (job.status === "done" || job.status === "failed" || job.status === "error") {
          window.clearInterval(pollingTimer);
          pollingTimer = null;
        }
      } catch (error) {
        if ($("task_placeholder")) $("task_placeholder").textContent = `任务状态刷新失败：${error.message}`;
        window.clearInterval(pollingTimer);
        pollingTimer = null;
      }
    }, 2000);
  } catch (error) {
    if ($("task_detail_status")) $("task_detail_status").textContent = "加载失败";
    if ($("task_detail_subtitle")) $("task_detail_subtitle").textContent = error.message;
    if ($("task_placeholder")) $("task_placeholder").textContent = `无法读取任务：${error.message}`;
  }
}

function providerFieldValue(config, field) {
  const value = (config.provider_config_json || {})[field.key];
  if (field.kind === "checkbox") return Boolean(value);
  return value ?? "";
}

function renderProviderConfigCard(config) {
  const fields = config.config_fields || [];
  const credentials = fields.filter((field) => field.key === "app_key" || field.key === "app_secret");
  const requestFields = fields.filter((field) => field.key === "req_key" || field.key === "base_url");
  const modeFields = fields.filter((field) => field.key === "mock_mode");
  const statusText = config.is_valid ? "配置已校验，可以直接在工作区使用。" : (config.last_error || "配置还未通过校验。");
  const renderField = (field) => `
    <label class="provider-field">
      <span>${field.label}</span>
      ${field.kind === "checkbox"
        ? `<input type="checkbox" data-provider-field="${config.provider_code}:${field.key}" ${providerFieldValue(config, field) ? "checked" : ""} />`
        : `<input type="${field.kind === "password" ? "password" : "text"}" data-provider-field="${config.provider_code}:${field.key}" value="${providerFieldValue(config, field)}" placeholder="${field.placeholder || ""}" ${field.required ? "required" : ""} />`}
      ${field.help_text ? `<small>${field.help_text}</small>` : ""}
    </label>
  `;
  return `
    <article class="provider-card provider-card--jimeng" data-provider-code="${config.provider_code}">
      <div class="provider-card__head">
        <div class="provider-card__title">
          <div class="provider-card__badge">云端视频 Provider</div>
          <h3>${config.display_name}</h3>
          <p>${config.description || ""}</p>
        </div>
        <div class="provider-card__status">
          <span class="task-card__badge task-card__badge--${config.is_valid ? "done" : "error"}">${config.is_valid ? "已校验" : "待配置"}</span>
          <span class="provider-card__status-text">${statusText}</span>
        </div>
      </div>

      <div class="provider-card__surface">
        <div class="provider-card__row">
          <label class="setting-toggle provider-card__toggle">
            <input type="checkbox" data-provider-toggle="${config.provider_code}" ${config.enabled ? "checked" : ""} />
            <span>启用即梦作为当前可选 Provider</span>
          </label>
          <div class="provider-card__meta">
            <span>Provider Code：${config.provider_code}</span>
            <span>最近校验：${parseDate(config.last_checked_at)}</span>
          </div>
        </div>

        <section class="provider-section">
          <div class="provider-section__head">
            <strong>基础凭证</strong>
            <span>保存即梦的账号鉴权信息</span>
          </div>
          <div class="provider-form provider-form--two-col">
            ${credentials.map(renderField).join("")}
          </div>
        </section>

        <section class="provider-section">
          <div class="provider-section__head">
            <strong>请求参数</strong>
            <span>控制默认 req_key 和接口访问地址</span>
          </div>
          <div class="provider-form provider-form--two-col">
            ${requestFields.map(renderField).join("")}
          </div>
        </section>

        <section class="provider-section">
          <div class="provider-section__head">
            <strong>开发模式</strong>
            <span>仅用于本地联调，不建议在真实环境启用</span>
          </div>
          <div class="provider-form provider-form--single">
            ${modeFields.map(renderField).join("")}
          </div>
        </section>
      </div>

      <div class="provider-card__actions">
        <button class="btn btn--ghost" type="button" data-provider-validate="${config.provider_code}">校验配置</button>
        <button class="btn btn--primary" type="button" data-provider-save="${config.provider_code}">保存配置</button>
      </div>
      <p class="provider-card__error" id="provider_error_${config.provider_code}">${config.last_error || ""}</p>
    </article>
  `;
}

function renderProvidersPage() {
  const list = $("providers_list");
  if (!list) return;
  if (!providerConfigs.length) {
    list.innerHTML = '<div class="tasks-empty"><h3>暂无 Provider 定义</h3><p>后端未返回任何 Provider 配置项。</p></div>';
    return;
  }
  list.innerHTML = providerConfigs.map(renderProviderConfigCard).join("");
}

function collectProviderForm(providerCode) {
  const config = providerConfigs.find((item) => item.provider_code === providerCode);
  if (!config) return { enabled: false, provider_config_json: {} };
  const payload = {};
  (config.config_fields || []).forEach((field) => {
    const node = document.querySelector(`[data-provider-field="${providerCode}:${field.key}"]`);
    if (!node) return;
    payload[field.key] = field.kind === "checkbox" ? node.checked : node.value.trim();
  });
  const enabledNode = document.querySelector(`[data-provider-toggle="${providerCode}"]`);
  return {
    enabled: Boolean(enabledNode?.checked),
    provider_config_json: payload,
  };
}

async function loadProviderConfigsIntoState() {
  providerConfigs = await fetchProviderConfigs();
  availableProviders = await fetchProviders();
}

async function initProvidersPage() {
  try {
    await loadProviderConfigsIntoState();
    renderProvidersPage();
  } catch (error) {
    const list = $("providers_list");
    if (list) {
      list.innerHTML = `<div class="tasks-empty"><h3>加载失败</h3><p>${error.message}</p></div>`;
    }
    return;
  }

  $("providers_refresh")?.addEventListener("click", async () => {
    await loadProviderConfigsIntoState();
    renderProvidersPage();
  });

  document.addEventListener("click", async (event) => {
    if (!pageIsProviders()) return;
    const validateButton = event.target.closest("[data-provider-validate]");
    const saveButton = event.target.closest("[data-provider-save]");
    if (!validateButton && !saveButton) return;

    const providerCode = validateButton?.dataset.providerValidate || saveButton?.dataset.providerSave;
    const payload = collectProviderForm(providerCode);
    const errorNode = $(`provider_error_${providerCode}`);
    if (errorNode) errorNode.textContent = "";

    try {
      if (validateButton) {
        const result = await validateProviderConfig(providerCode, payload.provider_config_json);
        if (errorNode) errorNode.textContent = result.ok ? "配置校验通过。" : (result.errors || []).join("；");
      }
      if (saveButton) {
        await updateProviderConfig(providerCode, payload);
        await loadProviderConfigsIntoState();
        renderProvidersPage();
      }
    } catch (error) {
      if (errorNode) errorNode.textContent = error.message;
    }
  });
}

if (pageIsStudio()) {
  initStudio();
}

if (pageIsTasks()) {
  initTasksPage();
}

if (pageIsTaskDetail()) {
  initTaskDetailPage();
}

if (pageIsProviders()) {
  initProvidersPage();
}
