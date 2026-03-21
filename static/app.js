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
  {
    id: "cute-card",
    name: "绘本卡通",
    description: "可爱、明快、适合故事化叙事。",
    mediaClass: "resource-card__media--cute",
    styleText: "storybook cartoon, playful framing, bright colors, character-centric scenes",
  },
  {
    id: "national-comic",
    name: "国漫",
    description: "国漫角色感和更强的节奏张力。",
    mediaClass: "",
    styleText: "modern Chinese animation, dynamic framing, vibrant textures, emotional storytelling",
  },
];

const mockCharacters = {
  public: [
    { id: "guard", name: "城门守卫", note: "铠甲、长枪、威严站姿", mediaClass: "resource-card__media--photo" },
    { id: "merchant", name: "商贩", note: "热闹叫卖，带生活感", mediaClass: "resource-card__media--cute" },
    { id: "musician", name: "宫廷乐师", note: "适合宴乐场景", mediaClass: "resource-card__media--comic" },
    { id: "dancer", name: "舞姬", note: "舞动镜头中的焦点角色", mediaClass: "resource-card__media--fantasy" },
    { id: "scholar", name: "文人", note: "茶楼、诗会、对谈", mediaClass: "" },
    { id: "girl", name: "少女", note: "温柔、青春、清新镜头", mediaClass: "resource-card__media--cute" },
    { id: "fox", name: "小狐狸", note: "灵动配角，增强童话感", mediaClass: "resource-card__media--comic" },
    { id: "cat", name: "猫咪", note: "适合宠物主角片段", mediaClass: "resource-card__media--photo" },
    { id: "rabbit", name: "小兔子", note: "轻盈、童趣", mediaClass: "resource-card__media--fantasy" },
  ],
  mine: [
    { id: "my-hero", name: "我的主角", note: "保留你的长期人设", mediaClass: "resource-card__media--photo" },
    { id: "my-pet", name: "我的宠物", note: "适合宠物故事长线角色", mediaClass: "resource-card__media--cute" },
    { id: "my-host", name: "我的主持人", note: "适合解说类视频", mediaClass: "" },
  ],
};

const mockVoices = [
  { id: "voice-story-f", name: "曼波讲故事", type: "热门", tone: "温柔叙述 · 女声" },
  { id: "voice-broadcast-m", name: "自然纪录片", type: "热门", tone: "沉稳旁白 · 男声" },
  { id: "voice-host-f", name: "知性女声", type: "推荐音乐", tone: "轻播音感 · 女声" },
  { id: "voice-youth-m", name: "清亮男声", type: "最新", tone: "年轻解说 · 男声" },
  { id: "voice-anime-f", name: "动漫少女", type: "超仿真", tone: "明亮角色感 · 女声" },
  { id: "voice-city-m", name: "城市小伙", type: "热门", tone: "生活化表达 · 男声" },
];

const mockMusic = [
  { id: "music-peace", name: "风（治愈纯音乐）", author: "治愈纯音乐", duration: "02:37", type: "推荐音乐" },
  { id: "music-ancient", name: "午后古巷轻松", author: "看见音乐", duration: "02:24", type: "推荐音乐" },
  { id: "music-warm", name: "欢快愉悦小调", author: "李闰驰", duration: "01:27", type: "热门" },
  { id: "music-epic", name: "企业宣传片明亮轻快", author: "逆理的钢琴师", duration: "03:48", type: "会员热榜" },
  { id: "music-phonk", name: "野马进行曲", author: "钰宝DJ钰", duration: "03:17", type: "热门" },
  { id: "music-bgm", name: "舒缓背景音乐 Full Track", author: "FiniteMusicForge", duration: "02:37", type: "推荐音乐" },
  { id: "music-drama", name: "科技未来", author: "Kerandino", duration: "01:59", type: "最新" },
];

const mockProviders = [
  {
    id: "kling",
    name: "Kling",
    note: "适合稳定的故事型视频生成，当前推荐默认选项。",
    capability: "故事感 / 叙事镜头",
  },
  {
    id: "openai",
    name: "OpenAI",
    note: "适合强调语言理解与镜头描述一致性。",
    capability: "语义理解 / 镜头还原",
  },
  {
    id: "gemini",
    name: "Gemini",
    note: "适合做多模态风格探索和快速试验。",
    capability: "风格探索 / 多模态",
  },
  {
    id: "doubao",
    name: "Doubao",
    note: "适合中文场景与本地化表达。",
    capability: "中文表达 / 本地化",
  },
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
  backend: "cloud",
  provider: "kling",
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
  topbarTab: null,
  jobsList: [],
};

let platformTemplates = [];
let pollingTimer = null;

function pageIsStudio() {
  return document.body.dataset.page === "studio";
}

function styleById(id) {
  return mockVisualStyles.find((item) => item.id === id) || mockVisualStyles[0];
}

function charactersByIds(ids) {
  return [...mockCharacters.public, ...mockCharacters.mine].filter((item) => ids.includes(item.id));
}

function defaultSceneCharacters(index) {
  const defaults = [
    ["guard", "merchant"],
    ["merchant", "scholar"],
    ["musician", "dancer"],
    ["girl", "fox"],
  ];
  return defaults[index] || ["my-pet"];
}

function buildDraftFromPrompt(prompt) {
  const clean = (prompt || "").trim();
  const topic = clean || "温暖的宠物奇遇故事";
  const style = styleById(state.visualStyleId);
  const baseCharacters = state.characterIds.length ? state.characterIds : ["my-pet", "girl"];
  const leadNames = charactersByIds(baseCharacters).map((item) => item.name).join("、") || "主角";

  const summary = `这个视频以“${topic}”为主线，通过 4 个分镜推进故事节奏。画面建议采用“${style.name}”风格，围绕 ${leadNames} 展开，从建立场景、进入情绪、推进故事到收束结尾，形成一支既可叙事又适合直接生成的视频草稿。`;

  const scenes = [
    {
      title: "开场建立",
      prompt: `以“${topic}”为主题的开场镜头，先建立世界观和空间氛围，让观众迅速进入故事。`,
      subtitle: `故事从这里开始：${topic}`,
      duration_s: 4,
      characterIds: baseCharacters,
    },
    {
      title: "角色登场",
      prompt: `主角 ${leadNames} 正式进入画面，镜头更贴近人物表情和动作，建立情绪联系。`,
      subtitle: `${leadNames} 的故事逐渐展开。`,
      duration_s: 4,
      characterIds: defaultSceneCharacters(1),
    },
    {
      title: "情绪推进",
      prompt: `通过更丰富的环境和动作细节推进故事，强化“${style.name}”的视觉氛围。`,
      subtitle: `情绪来到最饱满的一段。`,
      duration_s: 4,
      characterIds: defaultSceneCharacters(2),
    },
    {
      title: "收束结尾",
      prompt: `回到主角视角，用一个有余韵的镜头结束，形成完整闭环。`,
      subtitle: `故事在温柔的尾声里结束。`,
      duration_s: 4,
      characterIds: defaultSceneCharacters(3),
    },
  ];

  const storyText = scenes
    .map((scene, index) => `分镜${index + 1}：${scene.title}\n${scene.prompt}\n字幕：${scene.subtitle}`)
    .join("\n\n");

  return { summary, storyText, scenes };
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

function setDownloadState(enabled, href = "#") {
  const link = $("download_result");
  if (!link) return;
  link.href = href;
  link.setAttribute("aria-disabled", enabled ? "false" : "true");
  link.classList.toggle("is-disabled", !enabled);
}

function log(msg) {
  const el = $("log");
  if (!el) return;
  el.textContent += `${msg}\n`;
  el.scrollTop = el.scrollHeight;
}

async function parseErrorResponse(res) {
  const text = await res.text();
  try {
    const data = JSON.parse(text);
    return data.detail || text || `HTTP ${res.status}`;
  } catch {
    return text || `HTTP ${res.status}`;
  }
}

function setLoading(visible, text = "处理中...") {
  const overlay = $("loading_overlay");
  const textEl = $("loading_text");
  if (!overlay) return;
  overlay.style.display = visible ? "flex" : "none";
  if (textEl) textEl.textContent = text;
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
        let detail = `上传失败 (${xhr.status})`;
        try {
          const data = JSON.parse(xhr.responseText);
          detail = data.detail || detail;
        } catch {}
        reject(new Error(detail));
      }
    });
    xhr.addEventListener("error", () => reject(new Error("上传过程中网络异常")));
    xhr.send(formData);
  });
}

async function fetchJobs(limit = 20) {
  const res = await fetch(`/api/jobs?limit=${limit}`, { cache: "no-store" });
  if (!res.ok) throw new Error(await parseErrorResponse(res));
  const data = await res.json();
  return data.jobs || [];
}

async function fetchJob(jobId) {
  const res = await fetch(`/api/jobs/${jobId}`, { cache: "no-store" });
  if (!res.ok) throw new Error(await parseErrorResponse(res));
  return res.json();
}

async function fetchPlatformTemplates() {
  const res = await fetch("/api/platform-templates", { cache: "no-store" });
  if (!res.ok) throw new Error(await parseErrorResponse(res));
  const data = await res.json();
  return data.templates || [];
}

function renderAssistantThread() {
  const thread = $("assistant_thread");
  if (!thread) return;
  const prompt = state.assistantPrompt;
  if (!prompt) {
    thread.innerHTML = `
      <div class="chat-bubble chat-bubble--assistant">
        Hi，今天想做什么视频？把主题、情绪、角色关系或者镜头氛围告诉我，我会先给你一版故事和分镜草稿。
      </div>
    `;
    return;
  }
  thread.innerHTML = `
    <div class="chat-bubble chat-bubble--user">${prompt}</div>
    <div class="chat-bubble chat-bubble--assistant">
      视频策划方案已经备好，你可以继续在中间编辑故事、分镜和字幕，再从右侧选择画风、角色、配音和音乐。
    </div>
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
  summary.textContent = `当前共有 ${state.scenes.length} 个分镜，总时长约 ${totalDuration.toFixed(1)} 秒。已选角色 ${state.characterIds.length} 个，配音 ${selectedVoice()?.name || "未选"}，音乐 ${selectedMusic()?.name || "未选"}。`;
}

function renderSceneList() {
  const list = $("scene_list");
  if (!list) return;
  if (!state.scenes.length) {
    list.innerHTML = `
      <div class="scene-card">
        <div class="field-hint">这里会展示分镜卡片。你可以先在左侧生成一版故事，也可以直接新增分镜手动编辑。</div>
      </div>
    `;
    renderSceneSummary();
    return;
  }

  list.innerHTML = state.scenes
    .map((scene, index) => {
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
          <div class="scene-footer">
            ${roleTags || '<span class="field-hint">当前分镜还没有绑定角色，可从右侧角色库应用。</span>'}
          </div>
        </article>
      `;
    })
    .join("");

  renderSceneSummary();
}

function selectedVoice() {
  return mockVoices.find((item) => item.id === state.voiceId) || null;
}

function selectedMusic() {
  return mockMusic.find((item) => item.id === state.musicId) || null;
}

function renderTemplateSummary() {
  const summary = $("template_summary");
  if (!summary) return;
  const template = platformTemplates.find((item) => item.id === state.templateId);
  if (!template) {
    summary.textContent = "未选择模板，将使用当前比例和默认时长。";
    return;
  }
  summary.textContent = `${template.name} ｜ ${template.platform} ｜ ${template.width}×${template.height} ｜ ${template.duration_s}s`;
}

function renderResourceNote() {
  const note = $("resource_note");
  if (!note) return;
  const voice = selectedVoice();
  const music = selectedMusic();
  const provider = mockProviders.find((item) => item.id === state.provider);
  note.textContent = `已选画风：${styleById(state.visualStyleId).name}；角色：${state.characterIds.length} 个；提供商：${provider ? provider.name : "未选"}；配音：${voice ? voice.name : "未选"}；音乐：${music ? music.name : "未选"}。`;
}

function renderVisualTab() {
  return `
    <div class="panel-section">
      <h3>素材</h3>
      <div class="resource-grid">
        ${mockVisualStyles
          .map(
            (item) => `
              <article class="resource-card ${state.visualStyleId === item.id ? "is-selected" : ""}" data-style-id="${item.id}">
                <div class="resource-card__media ${item.mediaClass || ""}"></div>
                <strong>${item.name}</strong>
                <span>${item.description}</span>
              </article>
            `
          )
          .join("")}
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
        ${list
          .map(
            (item) => `
              <article class="character-card ${state.characterIds.includes(item.id) ? "is-selected" : ""}" data-character-id="${item.id}">
                <div class="character-card__media ${item.mediaClass || ""}"></div>
                <strong>${item.name}</strong>
                <span>${item.note}</span>
              </article>
            `
          )
          .join("")}
      </div>
    </div>
  `;
}

function renderProviderTab() {
  return `
    <div class="panel-section">
      <h3>提供商</h3>
      <h4>当前工作台固定走云端链路，选择不同 provider 控制生成模型表现。</h4>
      <div class="voice-list">
        ${mockProviders
          .map(
            (item) => `
              <article class="voice-item ${state.provider === item.id ? "is-selected" : ""}" data-provider-id="${item.id}">
                <div class="voice-item__meta">
                  <strong>${item.name}</strong>
                  <span>${item.note}</span>
                </div>
                <span>${item.capability}</span>
              </article>
            `
          )
          .join("")}
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
        ${["热门", "最新", "超仿真", "全部"]
          .map(
            (filter) => `
              <button class="filter-chip ${state.voiceFilter === filter ? "is-active" : ""}" data-voice-filter="${filter}">${filter}</button>
            `
          )
          .join("")}
      </div>
    </div>
    <div class="voice-list">
      ${list
        .map(
          (item) => `
            <article class="voice-item ${state.voiceId === item.id ? "is-selected" : ""}" data-voice-id="${item.id}">
              <div class="voice-item__meta">
                <strong>${item.name}</strong>
                <span>${item.tone}</span>
              </div>
              <span>${item.type}</span>
            </article>
          `
        )
        .join("")}
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
        <div class="field-hint">如果选择本地文件，会覆盖右侧已选音乐作为最终 BGM。</div>
      </div>
      <div class="setting-card" style="margin-top:10px;">
        <label for="bgm_volume">背景音乐音量</label>
        <input id="bgm_volume" type="number" value="${state.bgmVolume}" step="0.05" min="0" max="2" />
      </div>
    </div>
    <div class="panel-section">
      <div class="filter-row">
        ${["推荐音乐", "会员热榜", "热门", "最新", "全部"]
          .map(
            (filter) => `
              <button class="filter-chip ${state.musicFilter === filter ? "is-active" : ""}" data-music-filter="${filter}">${filter}</button>
            `
          )
          .join("")}
      </div>
    </div>
    <div class="music-list">
      <article class="music-item ${state.musicId === "none" ? "is-selected" : ""}" data-music-id="none">
        <div class="music-item__meta">
          <strong>无音乐</strong>
          <span>保留纯对白或字幕节奏</span>
        </div>
        <span>选项</span>
      </article>
      ${list
        .map(
          (item) => `
            <article class="music-item ${state.musicId === item.id ? "is-selected" : ""}" data-music-id="${item.id}">
              <div class="music-item__meta">
                <strong>${item.name}</strong>
                <span>${item.author} · ${item.duration}</span>
              </div>
              <span>${item.type}</span>
            </article>
          `
        )
        .join("")}
    </div>
  `;
}

function renderJobsTab() {
  if (state.jobsList.length === 0) {
    return `
      <div class="jobs-empty">
        <p>暂无任务记录</p>
      </div>
    `;
  }
  return `
    <div class="jobs-list">
      ${state.jobsList
        .map(
          (job) => `
            <div class="job-item">
              <span class="job-item__id">${job.id.slice(0, 8)}...</span>
              <span class="job-item__status job-item__status--${job.status}">${job.status}</span>
              <span class="job-item__stage">${job.stage || ""}</span>
            </div>
          `
        )
        .join("")}
    </div>
  `;
}

function renderResourcePanel() {
  const panel = $("resource_panel");
  const jobsPanel = $("jobs_panel");
  if (!panel) return;

  // Handle topbar tab switching
  if (state.topbarTab === "jobs") {
    panel.style.display = "none";
    if (jobsPanel) {
      jobsPanel.style.display = "block";
      jobsPanel.innerHTML = renderJobsTab();
    }
    document.querySelectorAll(".topbar-tab").forEach((button) => {
      button.classList.toggle("is-active", button.dataset.topbarTab === "jobs");
    });
    renderResourceNote();
    return;
  }

  panel.style.display = "block";
  if (jobsPanel) jobsPanel.style.display = "none";

  const map = {
    visual: renderVisualTab,
    character: renderCharacterTab,
    provider: renderProviderTab,
    voice: renderVoiceTab,
    music: renderMusicTab,
  };
  panel.innerHTML = map[state.activeTab]();

  document.querySelectorAll(".resource-tab").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.tab === state.activeTab);
  });

  document.querySelectorAll(".topbar-tab").forEach((button) => {
    button.classList.remove("is-active");
  });

  renderResourceNote();
}

function syncStudioInputs() {
  if ($("aspect_ratio")) $("aspect_ratio").value = state.aspectRatio;
  if ($("scene_type")) $("scene_type").value = state.sceneType;
  if ($("bgm_volume")) $("bgm_volume").value = String(state.bgmVolume);
  if ($("subtitles")) $("subtitles").checked = state.subtitles;
  if ($("template_id")) $("template_id").value = state.templateId;
  renderTemplateSummary();
}

function renderAll() {
  renderAssistantThread();
  renderAssistantPlan();
  renderStoryEditors();
  renderSceneList();
  renderResourcePanel();
  syncStudioInputs();
}

function updateStateFromStoryEditors() {
  state.storySummary = $("story_summary")?.value || "";
  state.storyText = $("story_text")?.value || "";
}

function sceneAt(index) {
  return state.scenes[index];
}

function toggleCharacterSelection(id) {
  const exists = state.characterIds.includes(id);
  state.characterIds = exists ? state.characterIds.filter((item) => item !== id) : [...state.characterIds, id];
  const scene = sceneAt(state.activeSceneIndex);
  if (scene) {
    const sceneHas = scene.characterIds.includes(id);
    scene.characterIds = sceneHas ? scene.characterIds.filter((item) => item !== id) : [...scene.characterIds, id];
  }
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

function moveScene(index, direction) {
  const target = index + direction;
  if (target < 0 || target >= state.scenes.length) return;
  const temp = state.scenes[index];
  state.scenes[index] = state.scenes[target];
  state.scenes[target] = temp;
  state.activeSceneIndex = target;
  renderAll();
}

function generateDraft() {
  const prompt = $("assistant_prompt")?.value.trim() || "";
  if (!prompt) {
    alert("先输入你想创作的视频主题。");
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
  const lines = [];
  if (job.stage) lines.push(`阶段：${job.stage}`);
  if (job.template_name) lines.push(`模板：${job.template_name}`);
  if (job.effective_backend) lines.push(`实际链路：${job.effective_backend}`);
  if (job.effective_provider) lines.push(`实际提供商：${job.effective_provider}`);
  if (job.image_count) lines.push(`参考图：${job.image_count}`);
  meta.textContent = lines.join(" ｜ ");
}

async function watchJob(jobId) {
  if (pollingTimer) window.clearInterval(pollingTimer);
  const hint = $("job_hint");
  const update = async () => {
    try {
      const job = await fetchJob(jobId);
      updateJobMeta(job);
      if (hint) hint.textContent = `当前任务：${job.status}${job.stage ? ` · ${job.stage}` : ""}`;
      log(`status: ${job.status}${job.stage ? ` (${job.stage})` : ""}`);
      if (job.status === "done") {
        setLoading(false);
        setGlobalStatus("生成完成", "done");
        setDownloadState(true, `/api/jobs/${jobId}/result`);
        if (hint) hint.textContent = "视频已生成完成，可以下载结果。";
        window.clearInterval(pollingTimer);
        pollingTimer = null;
      }
      if (job.status === "error") {
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
  await update();
  pollingTimer = window.setInterval(update, 1500);
}

async function submitJob() {
  updateStateFromStoryEditors();
  if (!state.scenes.length) {
    alert("先生成或新增至少一个分镜。");
    return;
  }

  const formData = new FormData();
  const prompt = state.assistantPrompt || state.storySummary || state.storyText || "Video storyboard draft";
  const storyboard = buildStoryboardPayload();
  const bgmFile = state.bgmFile;

  formData.append("prompt", prompt);
  formData.append("backend", "cloud");
  formData.append("provider", state.provider);
  formData.append("template_id", state.templateId || "");
  formData.append("subtitles", String(state.subtitles));
  formData.append("bgm_volume", String(state.bgmVolume));
  formData.append("storyboard_json", JSON.stringify(storyboard));
  if (bgmFile) formData.append("bgm", bgmFile);

  setLoading(true, "正在创建生成任务...");
  setGlobalStatus("正在创建任务", "running");
  setDownloadState(false);
  updateJobMeta(null);
  if ($("job_hint")) $("job_hint").textContent = "正在提交任务，请稍等...";
  $("log").textContent = "";

  try {
    const response = await uploadWithProgress(formData);
    state.lastJobId = response.job_id;
    log(`job_id: ${response.job_id}`);
    if ($("job_hint")) $("job_hint").textContent = "任务已提交，正在等待渲染反馈。";
    setGlobalStatus("生成中", "running");
    setLoading(true, "正在排队等待渲染...");
    await watchJob(response.job_id);
  } catch (error) {
    setLoading(false);
    setGlobalStatus("生成失败", "error");
    if ($("job_hint")) $("job_hint").textContent = `生成失败：${error.message}`;
    log(`ERROR: ${error.message}`);
    alert(`生成失败：${error.message}`);
  }
}

function attachStudioEvents() {
  $("assistant_generate")?.addEventListener("click", generateDraft);
  $("add_scene")?.addEventListener("click", addScene);
  $("submit")?.addEventListener("click", submitJob);

  $("story_summary")?.addEventListener("input", () => {
    state.storySummary = $("story_summary").value;
    renderAssistantPlan();
  });

  $("story_text")?.addEventListener("input", () => {
    state.storyText = $("story_text").value;
  });

  $("scene_type")?.addEventListener("change", (event) => {
    state.sceneType = event.target.value;
    renderAll();
  });

  document.addEventListener("click", (event) => {
    if (event.target.closest("textarea, input, select")) return;
    const target = event.target.closest("[data-tab], [data-topbar-tab], [data-style-id], [data-character-id], [data-character-scope], [data-provider-id], [data-voice-id], [data-music-id], [data-voice-filter], [data-music-filter], [data-action], .scene-card");
    if (!target) return;

    if (target.dataset.tab) {
      state.activeTab = target.dataset.tab;
      renderResourcePanel();
      return;
    }

    if (target.dataset.topbarTab) {
      state.topbarTab = target.dataset.topbarTab;
      if (state.topbarTab === "jobs") {
        fetchJobs().then((jobs) => {
          state.jobsList = jobs;
          renderResourcePanel();
        });
      } else {
        renderResourcePanel();
      }
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

    if (target.dataset.providerId) {
      state.provider = target.dataset.providerId;
      renderAll();
      return;
    }

    if (target.dataset.voiceId) {
      state.voiceId = target.dataset.voiceId;
      renderAll();
      return;
    }

    if (target.dataset.musicId) {
      state.musicId = target.dataset.musicId;
      renderAll();
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
    if (sceneCard?.dataset.sceneIndex) {
      state.activeSceneIndex = Number(sceneCard.dataset.sceneIndex);
      renderSceneList();
    }
  });

  document.addEventListener("input", (event) => {
    const sceneIndex = event.target.dataset.sceneIndex;
    const field = event.target.dataset.field;
    if (sceneIndex !== undefined && field) {
      const scene = sceneAt(Number(sceneIndex));
      if (!scene) return;
      scene[field] = field === "duration_s" ? Number(event.target.value) : event.target.value;
      if (field === "title" || field === "duration_s") renderSceneSummary();
      return;
    }

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

    if (event.target.id === "bgm_volume") {
      state.bgmVolume = Number(event.target.value);
    }
  });

  document.addEventListener("change", (event) => {
    if (event.target.id === "aspect_ratio") {
      state.aspectRatio = event.target.value;
      renderAll();
    }
    if (event.target.id === "template_id") {
      state.templateId = event.target.value;
      renderTemplateSummary();
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
  try {
    setGlobalStatus("空闲中", "idle");
    platformTemplates = await fetchPlatformTemplates();
    const select = $("template_id");
    if (select) {
      select.innerHTML = platformTemplates.map((item) => `<option value="${item.id}">${item.name}</option>`).join("");
      state.templateId = platformTemplates[0]?.id || "";
    }
    renderAll();
    attachStudioEvents();
  } catch (error) {
    setGlobalStatus("初始化失败", "error");
    if ($("job_hint")) $("job_hint").textContent = `初始化失败：${error.message}`;
  }
}

if (pageIsStudio()) {
  initStudio();
}
