const $ = (id) => document.getElementById(id);

const materialLibrary = {
  visuals: [],
  frames: [],
  characters: [],
  voices: [],
  music: [],
};

const state = {
  assistantPrompt: "",
  storySummary: "",
  storyText: "",
  scenes: [],
  visualStyleId: "",
  characterIds: [],
  voiceId: "",
  musicId: "",
  templateId: "",
  aspectRatio: "",
  sceneType: "智能分镜，图片 4.0，Seedance 1.0",
  subtitles: true,
  bgmVolume: 0.25,
  provider: "",
  storyAssistantCode: "",
  characterImageAssistantCode: "",
  activeTab: "visual",
  characterGroup: "",
  characterBindingMode: false,
  frameBindingMode: false,
  parsedCharacters: [],
  selectedParsedCharacterId: "",
  openingFrame: { source_type: "empty", asset_id: "", preview_url: "", file: null, status: "idle", error: "" },
  endingFrame: { source_type: "empty", asset_id: "", preview_url: "", file: null, status: "idle", error: "" },
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
let availableStoryAssistants = [];
let availableCharacterImageAssistants = [];
let providerConfigs = [];
let storyAssistantConfigs = [];
let characterImageAssistantConfigs = [];
let materialConfigs = { visuals: [], frames: [], characters: [], voices: [], music: [] };
let platformTemplates = [];
let pollingTimer = null;
let activeMaterialConfigTab = "visuals";
let activeConfigTab = "providers";
let activeConfigSection = "jimeng";
const pendingMaterialDrafts = { visuals: [], frames: [], characters: [], voices: [], music: [] };
const pendingStoryAssistantDrafts = [];
const pendingCharacterImageAssistantDrafts = [];
const pendingCustomProviderDrafts = [];
const materialUploadFiles = new Map();
const materialPreviewUrls = new Map();
const materialUploadNames = new Map();

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

function materialsOf(type) {
  return materialLibrary[type] || [];
}

function styleById(id) {
  return materialsOf("visuals").find((item) => item.id === id) || materialsOf("visuals")[0] || null;
}

function imageThumb(url, alt = "") {
  if (!url) return '<div class="resource-card__media resource-card__media--placeholder"></div>';
  return `<div class="resource-card__media resource-card__media--image"><img src="${url}" alt="${alt}" loading="lazy" /></div>`;
}

function audioPreview(url) {
  if (!url) return '<div class="resource-audio resource-audio--empty">未上传音频</div>';
  return `<audio class="resource-audio" controls preload="none" src="${url}"></audio>`;
}

function selectedVoice() {
  return materialsOf("voices").find((item) => item.id === state.voiceId) || null;
}

function selectedMusic() {
  return materialsOf("music").find((item) => item.id === state.musicId) || null;
}

function selectedProvider() {
  return availableProviders.find((item) => item.provider_code === state.provider) || null;
}

function charactersByIds(ids) {
  return materialsOf("characters").filter((item) => ids.includes(item.id));
}

function materialDraftKey(type, id) {
  return `${type}:${id}`;
}

function fileNameLabel(name = "") {
  if (!name) return "尚未选择文件";
  return name.length > 28 ? `${name.slice(0, 25)}...` : name;
}

function revokeMaterialPreview(key) {
  const current = materialPreviewUrls.get(key);
  if (current) URL.revokeObjectURL(current);
  materialPreviewUrls.delete(key);
}

function clearMaterialUploadState(key) {
  materialUploadFiles.delete(key);
  materialUploadNames.delete(key);
  revokeMaterialPreview(key);
}

function setMaterialUploadState(key, file) {
  clearMaterialUploadState(key);
  if (!file) return;
  materialUploadFiles.set(key, file);
  materialUploadNames.set(key, file.name || "");
  if (file.type.startsWith("image/")) {
    materialPreviewUrls.set(key, URL.createObjectURL(file));
  }
}

function uploadedMaterialFile(key) {
  return materialUploadFiles.get(key) || null;
}

function uploadedMaterialFileName(key) {
  return materialUploadNames.get(key) || "";
}

function uploadFileNameLabel(file) {
  return fileNameLabel(file?.name || "");
}

function configOptionMarkup(label = "去配置") {
  return `<option value="__config__">${label}</option>`;
}

function navigateToConfigTab(tab, section = "") {
  const query = new URLSearchParams({ tab });
  if (section) query.set("section", section);
  window.location.href = `/config?${query.toString()}`;
}

function frameState(type) {
  return type === "opening" ? state.openingFrame : state.endingFrame;
}

function setFrameState(type, payload) {
  if (type === "opening") {
    state.openingFrame = { ...state.openingFrame, ...payload };
    return;
  }
  state.endingFrame = { ...state.endingFrame, ...payload };
}

function frameSourceValue(type) {
  const current = frameState(type);
  return current?.source_type && current.source_type !== "empty" ? current.source_type : "";
}

function clearFrameState(type) {
  setFrameState(type, {
    source_type: "empty",
    asset_id: "",
    preview_url: "",
    file: null,
    status: "idle",
    error: "",
  });
}

function selectedImageAssistant() {
  return availableCharacterImageAssistants.find((item) => item.assistant_code === state.characterImageAssistantCode) || null;
}

function characterGroups() {
  const groups = [...new Set(materialsOf("characters").map((item) => item.group_name || "默认分组").filter(Boolean))];
  return groups.length ? groups : ["默认分组"];
}

function storySettingFromText(text) {
  const clean = (text || "").trim();
  if (!clean) return "";
  return clean.replace(/【分镜脚本】[\s\S]*$/u, "").trim();
}

function slugifyRoleName(name, index) {
  const ascii = String(name || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return ascii || `role-${index + 1}`;
}

function normalizeRoleLine(line) {
  return String(line || "")
    .replace(/^[\-\u2022]\s*/, "")
    .replace(/^\d+[\.\u3001\)]\s*/, "")
    .trim();
}

function parseCharactersFromStoryText(text) {
  const clean = String(text || "").trim();
  if (!clean) return [];
  const match = clean.match(/【角色列表】\s*([\s\S]*?)(?:\n\s*【|$)/u);
  const block = match?.[1]?.trim();
  if (!block) return [];
  return block
    .split(/\n+/)
    .map((line) => normalizeRoleLine(line))
    .filter(Boolean)
    .map((line, index) => {
      const parts = line.split(/[：:]/);
      const name = (parts.shift() || `角色${index + 1}`).trim();
      const description = parts.join("：").trim();
      return {
        draft_character_id: `parsed:${slugifyRoleName(name, index)}`,
        name: name || `角色${index + 1}`,
        description: description || "",
        bound_material_id: "",
        generation_status: "idle",
        preview_image_url: "",
        normalized_prompt: "",
        error: "",
      };
    });
}

function autoBindParsedCharacters(parsedCharacters) {
  return parsedCharacters.map((item) => {
    const exact = materialsOf("characters").find((material) => material.name === item.name);
    const fuzzy = exact || materialsOf("characters").find((material) => {
      const source = `${material.name}${material.description || ""}`.toLowerCase();
      return source.includes(item.name.toLowerCase());
    });
    return {
      ...item,
      bound_material_id: item.bound_material_id || fuzzy?.id || "",
    };
  });
}

function mergeParsedCharacters(parsedCharacters) {
  const previous = new Map(
    (state.parsedCharacters || []).map((item) => [
      item.draft_character_id,
      item,
    ]),
  );
  const merged = autoBindParsedCharacters(parsedCharacters).map((item) => {
    const saved = previous.get(item.draft_character_id);
    if (!saved) return item;
    const bindingValid = !saved.bound_material_id || materialsOf("characters").some((material) => material.id === saved.bound_material_id);
    return {
      ...item,
      bound_material_id: bindingValid ? saved.bound_material_id : item.bound_material_id,
      generation_status: saved.generation_status === "preview" && saved.preview_image_url ? "preview" : "idle",
      preview_image_url: saved.preview_image_url || "",
      normalized_prompt: saved.normalized_prompt || "",
      error: bindingValid ? "" : "角色素材已失效，请重新确认绑定",
    };
  });
  state.parsedCharacters = merged;
  if (!merged.some((item) => item.draft_character_id === state.selectedParsedCharacterId)) {
    state.selectedParsedCharacterId = merged[0]?.draft_character_id || "";
  }
  syncCharacterIdsFromBindings();
}

function parsedCharacterById(id) {
  return (state.parsedCharacters || []).find((item) => item.draft_character_id === id) || null;
}

function selectedParsedCharacter() {
  return parsedCharacterById(state.selectedParsedCharacterId);
}

function syncCharacterIdsFromBindings() {
  const bindingIds = [...new Set((state.parsedCharacters || []).map((item) => item.bound_material_id).filter(Boolean))];
  if (!state.parsedCharacters.length && !state.characterBindingMode) return;
  state.characterIds = bindingIds;
  state.scenes = (state.scenes || []).map((scene) => ({ ...scene, characterIds: [...bindingIds] }));
}

function inferAspectRatio(width, height) {
  const known = {
    "16:9": [16, 9],
    "9:16": [9, 16],
    "1:1": [1, 1],
    "4:3": [4, 3],
    "3:4": [3, 4],
    "21:9": [21, 9],
  };
  if (!width || !height) return "16:9";
  const ratio = Number(width) / Number(height);
  for (const [label, pair] of Object.entries(known)) {
    if (Math.abs(ratio - (pair[0] / pair[1])) < 0.03) return label;
  }
  return `${width}:${height}`;
}

function aspectDimensions(ratio) {
  const map = {
    "16:9": { width: 1280, height: 720 },
    "9:16": { width: 1080, height: 1920 },
    "1:1": { width: 1080, height: 1080 },
    "4:3": { width: 1280, height: 960 },
    "3:4": { width: 1080, height: 1440 },
    "21:9": { width: 1680, height: 720 },
  };
  return map[ratio] || map["16:9"];
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

async function fetchStoryAssistants() {
  const data = await fetchJson("/api/story-assistants", { cache: "no-store" });
  return data.story_assistants || [];
}

async function fetchStoryAssistantConfigs() {
  const data = await fetchJson("/api/story-assistant-configs", { cache: "no-store" });
  return data.story_assistant_configs || [];
}

async function fetchCharacterImageAssistants() {
  const data = await fetchJson("/api/character-image-assistants", { cache: "no-store" });
  return data.character_image_assistants || [];
}

async function fetchCharacterImageAssistantConfigs() {
  const data = await fetchJson("/api/character-image-assistant-configs", { cache: "no-store" });
  return data.character_image_assistant_configs || [];
}

async function fetchMaterials() {
  const data = await fetchJson("/api/materials", { cache: "no-store" });
  return {
    visuals: data.visuals || [],
    frames: data.frames || [],
    characters: data.characters || [],
    voices: data.voices || [],
    music: data.music || [],
  };
}

async function fetchMaterialConfigs() {
  const data = await fetchJson("/api/material-configs", { cache: "no-store" });
  return {
    visuals: data.visuals || [],
    frames: data.frames || [],
    characters: data.characters || [],
    voices: data.voices || [],
    music: data.music || [],
  };
}

async function createMaterialConfig(type, item, file) {
  const formData = new FormData();
  formData.append("metadata_json", JSON.stringify(item));
  if (file) formData.append("file", file);
  return fetchJson(`/api/material-configs/${type}`, {
    method: "POST",
    body: formData,
  });
}

async function updateMaterialConfig(type, id, item, file = null) {
  const formData = new FormData();
  formData.append("metadata_json", JSON.stringify(item));
  if (file) formData.append("file", file);
  return fetchJson(`/api/material-configs/${type}/${id}`, {
    method: "PUT",
    body: formData,
  });
}

async function deleteMaterialConfig(type, id) {
  return fetchJson(`/api/material-configs/${type}/${id}`, { method: "DELETE" });
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

async function updateStoryAssistantConfig(assistantCode, payload) {
  return fetchJson(`/api/story-assistant-configs/${assistantCode}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

async function validateStoryAssistantConfig(assistantCode, payload) {
  return fetchJson(`/api/story-assistant-configs/${assistantCode}/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

async function updateCharacterImageAssistantConfig(assistantCode, payload) {
  return fetchJson(`/api/character-image-assistant-configs/${assistantCode}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

async function validateCharacterImageAssistantConfig(assistantCode, payload) {
  return fetchJson(`/api/character-image-assistant-configs/${assistantCode}/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

async function generateStoryDraft(payload) {
  return fetchJson("/api/story-assistants/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

async function generateCharacterImage(payload) {
  return fetchJson("/api/character-image-assistants/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

async function confirmCharacterImage(payload) {
  return fetchJson("/api/character-image-assistants/confirm", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
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
      characterIds: [...state.characterIds],
    },
    {
      title: "角色登场",
      prompt: `主角 ${leadNames} 正式进入画面，镜头更贴近人物表情和动作，建立情绪联系。`,
      subtitle: `${leadNames} 的故事逐渐展开。`,
      duration_s: 4,
      characterIds: [...state.characterIds],
    },
    {
      title: "情绪推进",
      prompt: `通过更丰富的环境和动作细节推进故事，强化“${style.name}”的视觉氛围。`,
      subtitle: `情绪来到最饱满的一段。`,
      duration_s: 4,
      characterIds: [...state.characterIds],
    },
    {
      title: "收束结尾",
      prompt: `回到主角视角，用一个有余韵的镜头结束，形成完整闭环。`,
      subtitle: "故事在温柔的尾声里结束。",
      duration_s: 4,
      characterIds: [...state.characterIds],
    },
  ];
  const summary = `这个视频以“${clean}”为主线，通过 ${scenes.length} 个分镜推进故事节奏。画面建议采用“${style?.name || "默认风格"}”风格，并以 ${leadNames} 为核心完成一支可直接提交生成的视频草稿。`;
  const storyText = buildStoryDocument(summary, scenes);
  return { summary, storyText, scenes };
}

function buildStoryDocument(summary, scenes) {
  const roleMap = new Map();
  scenes.forEach((scene) => {
    charactersByIds(scene.characterIds || []).forEach((character) => {
      if (!roleMap.has(character.id)) roleMap.set(character.id, character);
    });
  });
  const roleLines = roleMap.size
    ? Array.from(roleMap.values()).map((character, index) => `${index + 1}. ${character.name}：${character.description || "待补充角色描述"}`).join("\n")
    : "1. 暂无角色设定，请从右侧角色库补充。";
  const sceneLines = scenes.map((scene, index) => {
    const block = [
      `分镜${index + 1}：${scene.title || `分镜 ${index + 1}`}`,
      scene.prompt || "",
    ];
    if (scene.subtitle) block.push(`字幕：${scene.subtitle}`);
    return block.filter(Boolean).join("\n");
  }).join("\n\n");
  return `【内容概览】\n${summary || "待补充视频概览。"}\n\n【角色列表】\n${roleLines}\n\n【分镜脚本】\n${sceneLines || "待生成分镜脚本。"}`;
}

function documentSummary(text) {
  const clean = (text || "").trim();
  if (!clean) return state.storySummary || "";
  const summaryMatch = clean.match(/【内容概览】\s*([\s\S]*?)(?:\n\s*【|$)/);
  if (summaryMatch?.[1]) return summaryMatch[1].trim();
  return clean.split("\n").find((line) => line.trim()) || "";
}

function renderAssistantThread() {
  const thread = $("assistant_thread");
  if (!thread) return;
  if (!availableStoryAssistants.length) {
    thread.innerHTML = '<div class="chat-bubble chat-bubble--assistant">暂无可用故事助手。请先到配置中心完成模型 URL、API Key 和 Model 配置。</div>';
    return;
  }
  if (!state.assistantPrompt) {
    thread.innerHTML = '<div class="chat-bubble chat-bubble--assistant">Hi，今天想做什么视频？把主题、情绪、角色关系或者镜头氛围告诉我，我会先给你一版故事和分镜草稿。</div>';
    return;
  }
  thread.innerHTML = `<div class="chat-bubble chat-bubble--user">${state.assistantPrompt}</div>`;
}

function renderAssistantPlan() {
  const plan = $("assistant_plan");
  if (!plan) return;
  if (!availableStoryAssistants.length || !state.storySummary) {
    plan.innerHTML = "";
    return;
  }
  plan.innerHTML = `
      <div class="assistant-card">
        <h3>策划案已生成</h3>
        <div class="assistant-card__meta">${styleById(state.visualStyleId)?.name || "默认风格"} · ${state.scenes.length} 个分镜 · ${state.aspectRatio || "未设置比例"}</div>
        <div class="assistant-card__summary">${state.storySummary}</div>
      </div>
  `;
}

function renderStoryAssistantSelect() {
  const select = $("story_assistant_select");
  const button = $("assistant_generate");
  if (!select || !button) return;
  if (!availableStoryAssistants.length) {
    select.innerHTML = `<option value="">暂无可用故事助手</option>${configOptionMarkup("去配置故事助手")}`;
    select.disabled = false;
    state.storyAssistantCode = "";
    button.disabled = true;
    button.textContent = "请先配置故事助手";
    return;
  }
  select.disabled = false;
  select.innerHTML = `${availableStoryAssistants.map((item) => `<option value="${item.assistant_code}">${item.display_name}</option>`).join("")}${configOptionMarkup("去配置故事助手")}`;
  if (!state.storyAssistantCode || !availableStoryAssistants.some((item) => item.assistant_code === state.storyAssistantCode)) {
    state.storyAssistantCode = availableStoryAssistants[0].assistant_code;
  }
  select.value = state.storyAssistantCode;
  button.disabled = false;
  button.textContent = "生成故事与分镜";
}

function renderImageAssistantSelect() {
  const select = $("image_assistant_select");
  if (!select) return;
  if (!availableCharacterImageAssistants.length) {
    select.innerHTML = `<option value="">暂无可用生图助手</option>${configOptionMarkup("去配置生图助手")}`;
    select.disabled = false;
    state.characterImageAssistantCode = "";
    return;
  }
  select.disabled = false;
  select.innerHTML = `${availableCharacterImageAssistants.map((item) => `<option value="${item.assistant_code}">${item.display_name}</option>`).join("")}${configOptionMarkup("去配置生图助手")}`;
  if (!state.characterImageAssistantCode || !availableCharacterImageAssistants.some((item) => item.assistant_code === state.characterImageAssistantCode)) {
    state.characterImageAssistantCode = availableCharacterImageAssistants[0].assistant_code;
  }
  select.value = state.characterImageAssistantCode;
}

function renderStoryEditors() {
  const node = $("story_document");
  if (!node) return;
  node.value = state.storyText;
  $("character_binding_toggle")?.classList.toggle("is-active", state.characterBindingMode);
  $("frame_binding_toggle")?.classList.toggle("is-active", state.frameBindingMode);
}

function parseAndOpenCharacterBinding() {
  state.storyText = $("story_document")?.value || state.storyText;
  const parsed = parseCharactersFromStoryText(state.storyText);
  if (!parsed.length) {
    window.alert("正文里的【角色列表】为空，先生成或补充角色文本。");
    return;
  }
  mergeParsedCharacters(parsed);
  state.characterBindingMode = true;
  state.frameBindingMode = false;
  state.activeTab = "character";
  renderAll();
}

function exitCharacterBindingMode() {
  state.characterBindingMode = false;
  renderAll();
}

function openFrameBindingMode() {
  state.frameBindingMode = true;
  state.characterBindingMode = false;
  state.activeTab = "frames";
  renderAll();
}

function exitFrameBindingMode() {
  state.frameBindingMode = false;
  renderAll();
}

function setParsedCharacterBinding(draftCharacterId, materialId) {
  state.parsedCharacters = (state.parsedCharacters || []).map((item) => (
    item.draft_character_id === draftCharacterId
      ? {
          ...item,
          bound_material_id: materialId,
          preview_image_url: materialId ? "" : item.preview_image_url,
          generation_status: materialId ? "bound" : "idle",
          error: "",
        }
      : item
  ));
  syncCharacterIdsFromBindings();
  renderAll();
}

async function generateSelectedCharacterPreview() {
  const current = selectedParsedCharacter();
  if (!current) {
    window.alert("先在右侧选择一个待处理角色。");
    return;
  }
  if (!availableCharacterImageAssistants.length || !state.characterImageAssistantCode) {
    window.alert("请先在配置中心配置可用的生图助手。");
    return;
  }
  state.parsedCharacters = state.parsedCharacters.map((item) => (
    item.draft_character_id === current.draft_character_id
      ? { ...item, generation_status: "generating", error: "" }
      : item
  ));
  renderResourcePanel();
  try {
    const style = styleById(state.visualStyleId);
    const result = await generateCharacterImage({
      assistant_code: state.characterImageAssistantCode,
      character_name: current.name,
      character_description: current.description || "",
      story_summary: state.storySummary || documentSummary(state.storyText),
      story_setting: storySettingFromText(state.storyText),
      visual_style_name: style?.name || "",
      visual_style_prompt: style?.prompt_fragment || "",
    });
    state.parsedCharacters = state.parsedCharacters.map((item) => (
      item.draft_character_id === current.draft_character_id
        ? {
            ...item,
            preview_image_url: result.preview_image_url || "",
            normalized_prompt: result.normalized_prompt || "",
            generation_status: "preview",
            error: "",
          }
        : item
    ));
  } catch (error) {
    state.parsedCharacters = state.parsedCharacters.map((item) => (
      item.draft_character_id === current.draft_character_id
        ? { ...item, generation_status: "error", error: error.message }
        : item
    ));
  }
  renderResourcePanel();
}

async function confirmSelectedCharacterPreview() {
  const current = selectedParsedCharacter();
  if (!current?.preview_image_url) {
    window.alert("当前角色还没有可确认的预览图。");
    return;
  }
  try {
    const response = await confirmCharacterImage({
      preview_image_url: current.preview_image_url,
      name: current.name,
      description: current.description || "",
      prompt_fragment: current.normalized_prompt || current.description || "",
      group_name: state.characterGroup || "默认分组",
      sort_order: 100,
    });
    const item = response.item;
    Object.assign(materialLibrary, await fetchMaterials());
    state.characterGroup = item.group_name || state.characterGroup;
    state.parsedCharacters = state.parsedCharacters.map((entry) => (
      entry.draft_character_id === current.draft_character_id
        ? {
            ...entry,
            bound_material_id: item.id,
            preview_image_url: "",
            normalized_prompt: current.normalized_prompt,
            generation_status: "bound",
            error: "",
          }
        : entry
    ));
    syncCharacterIdsFromBindings();
    renderAll();
  } catch (error) {
    window.alert(`角色预览确认失败：${error.message}`);
  }
}

function discardSelectedCharacterPreview() {
  const current = selectedParsedCharacter();
  if (!current) return;
  state.parsedCharacters = state.parsedCharacters.map((item) => (
    item.draft_character_id === current.draft_character_id
      ? { ...item, preview_image_url: "", normalized_prompt: "", generation_status: item.bound_material_id ? "bound" : "idle", error: "" }
      : item
  ));
  renderResourcePanel();
}

function frameScene(type) {
  if (!state.scenes.length) return null;
  return type === "opening" ? state.scenes[0] : state.scenes[state.scenes.length - 1];
}

function frameLabel(type) {
  return type === "opening" ? "首帧图" : "尾帧图";
}

function setFrameSource(type, sourceType) {
  if (!sourceType) {
    clearFrameState(type);
    renderResourcePanel();
    return;
  }
  const current = frameState(type);
  if (current?.source_type === "upload" && current.preview_url) {
    URL.revokeObjectURL(current.preview_url);
  }
  setFrameState(type, {
    source_type: sourceType,
    asset_id: "",
    preview_url: "",
    file: null,
    status: "idle",
    error: "",
  });
  renderResourcePanel();
}

async function generateFramePreview(type) {
  const scene = frameScene(type);
  if (!scene) {
    window.alert("先生成或补充分镜脚本，再生成首尾帧图片。");
    return;
  }
  const assistant = selectedImageAssistant();
  if (!assistant) {
    window.alert("请先在配置中心配置可用的生图助手。");
    return;
  }
  setFrameState(type, { status: "generating", error: "" });
  renderResourcePanel();
  try {
    const style = styleById(state.visualStyleId);
    const promptTitle = type === "opening" ? "视频首帧参考图" : "视频尾帧参考图";
    const result = await generateCharacterImage({
      assistant_code: assistant.assistant_code,
      character_name: promptTitle,
      character_description: `${scene.title || promptTitle}：${scene.prompt || ""}`,
      story_summary: state.storySummary || documentSummary(state.storyText),
      story_setting: storySettingFromText(state.storyText),
      visual_style_name: style?.name || "",
      visual_style_prompt: style?.prompt_fragment || "",
    });
    setFrameState(type, {
      source_type: "generated",
      asset_id: "",
      preview_url: result.preview_image_url || "",
      file: null,
      status: "ready",
      error: "",
    });
  } catch (error) {
    setFrameState(type, { status: "error", error: error.message });
  }
  renderResourcePanel();
}

function selectFrameFromLibrary(type, assetId) {
  const asset = materialsOf("frames").find((item) => item.id === assetId);
  if (!asset) return;
  setFrameState(type, {
    source_type: "library",
    asset_id: asset.id,
    preview_url: asset.cover_url || asset.public_url || "",
    file: null,
    status: "ready",
    error: "",
  });
  renderResourcePanel();
}

function setFrameUpload(type, file) {
  if (!file) {
    clearFrameState(type);
    renderResourcePanel();
    return;
  }
  const nextUrl = URL.createObjectURL(file);
  const current = frameState(type);
  if (current?.source_type === "upload" && current.preview_url) {
    URL.revokeObjectURL(current.preview_url);
  }
  setFrameState(type, {
    source_type: "upload",
    asset_id: "",
    preview_url: nextUrl,
    file,
    status: "ready",
    error: "",
  });
  renderResourcePanel();
}

function clearFrameSelection(type) {
  const current = frameState(type);
  if (current?.source_type === "upload" && current.preview_url) {
    URL.revokeObjectURL(current.preview_url);
  }
  setFrameState(type, {
    asset_id: "",
    preview_url: "",
    file: null,
    status: "idle",
    error: "",
  });
  renderResourcePanel();
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
    select.innerHTML = `<option value="">暂无可用视频助手</option>${configOptionMarkup("去配置视频助手")}`;
    state.provider = "";
    return;
  }
  select.innerHTML = `${availableProviders.map((item) => `<option value="${item.provider_code}">${item.display_name}</option>`).join("")}${configOptionMarkup("去配置视频助手")}`;
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
  const imageAssistant = selectedImageAssistant();
  const boundCharacterIds = [...new Set((state.parsedCharacters || []).map((item) => item.bound_material_id).filter(Boolean))];
  const effectiveCharacterCount = boundCharacterIds.length || state.characterIds.length;
  note.textContent = `已选画面：${styleById(state.visualStyleId)?.name || "未选"}；首帧：${state.openingFrame.source_type === "empty" ? "未选" : "已绑定"}；尾帧：${state.endingFrame.source_type === "empty" ? "未选" : "已绑定"}；角色：${effectiveCharacterCount} 个；生图助手：${imageAssistant ? imageAssistant.display_name : "未配置"}；视频助手：${provider ? provider.display_name : "未配置"}；配音：${voice ? voice.name : "未选"}；音乐：${music ? music.name : "未选"}。`;
}

function renderVisualTab() {
  const visuals = materialsOf("visuals");
  return `
    <div class="panel-section">
      <h3>素材</h3>
      <div class="resource-grid">
        ${visuals.map((item) => `
          <article class="resource-card ${state.visualStyleId === item.id ? "is-selected" : ""}" data-style-id="${item.id}">
            ${imageThumb(item.cover_url || item.public_url, item.name)}
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
          <option value="3:4" ${state.aspectRatio === "3:4" ? "selected" : ""}>3:4</option>
          <option value="21:9" ${state.aspectRatio === "21:9" ? "selected" : ""}>21:9</option>
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

function renderFramesTab() {
  const frameAssets = materialsOf("frames");
  const renderFrameCard = (type) => {
    const current = frameState(type);
    const source = frameSourceValue(type);
    const selectedAssetId = current.source_type === "library" ? current.asset_id : "";
    const statusText = current.status === "generating"
      ? "生成中"
      : current.error
        ? current.error
        : current.source_type === "library"
          ? "已从首尾帧素材库绑定"
          : current.source_type === "upload"
            ? "已上传当前任务图片"
            : current.source_type === "generated"
              ? "已生成预览图"
              : "未绑定";
    const sourcePanel = source === "generated"
      ? `
        <div class="frame-card__source-panel">
          <div class="frame-card__source-copy">
            <strong>根据分镜脚本生成</strong>
            <span>会结合当前故事概览、角色和画面风格生成 ${frameLabel(type)} 预览图。</span>
          </div>
          <button class="btn btn--ghost" type="button" data-frame-generate="${type}" ${selectedImageAssistant() ? "" : "disabled"}>${current.status === "generating" ? "生成中..." : `生成${frameLabel(type)}`}</button>
        </div>
      `
      : source === "upload"
        ? `
          <div class="frame-card__source-panel">
            <div class="frame-card__source-copy">
              <strong>上传当前任务图片</strong>
              <span>上传的图片只在当前任务中使用，不会自动保存到首尾帧素材库。</span>
            </div>
            <label class="upload-picker">
              <input class="upload-picker__input" type="file" accept="image/*" data-frame-upload="${type}" />
              <span class="upload-picker__button">${current.file ? "替换图片" : "选择图片"}</span>
              <span class="upload-picker__meta">${current.file ? uploadFileNameLabel(current.file) : "支持 PNG、JPG、WEBP 等常见图片格式"}</span>
            </label>
          </div>
        `
        : source === "library"
          ? `
            <label class="provider-field frame-card__source-panel">
              <span>从首尾帧素材库选择</span>
              <select data-frame-select="${type}">
                <option value="">未选择</option>
                ${frameAssets.map((item) => `<option value="${item.id}" ${item.id === selectedAssetId ? "selected" : ""}>${item.name}</option>`).join("")}
              </select>
              <small>这里是独立于画面素材库的首尾帧资源池，适合管理统一的开场图和结尾图。</small>
            </label>
          `
          : `
            <div class="frame-card__source-panel frame-card__source-panel--empty">
              <span>先选择来源，再决定是生成图片、上传图片，还是从首尾帧素材库里复用现有图片。</span>
            </div>
          `;
    return `
      <div class="setting-card frame-card ${state.frameBindingMode ? "is-active" : ""}">
        <div class="frame-card__head">
          <div>
            <h4>${frameLabel(type)}</h4>
            <p>${statusText}</p>
          </div>
        </div>
        <div class="frame-card__preview">
          ${current.preview_url ? `<img src="${current.preview_url}" alt="${frameLabel(type)}" loading="lazy" />` : '<div class="frame-card__placeholder">暂无图片</div>'}
        </div>
        <div class="frame-card__controls">
          <label class="provider-field">
            <span>图片来源</span>
            <select data-frame-source="${type}">
              <option value="">请选择</option>
              <option value="generated" ${source === "generated" ? "selected" : ""}>根据分镜脚本生成</option>
              <option value="upload" ${source === "upload" ? "selected" : ""}>上传当前任务图片</option>
              <option value="library" ${source === "library" ? "selected" : ""}>从素材库选择</option>
            </select>
          </label>
          ${sourcePanel}
          <button class="btn btn--secondary" type="button" data-frame-clear="${type}" ${current.source_type === "empty" ? "disabled" : ""}>清除${frameLabel(type)}</button>
        </div>
      </div>
    `;
  };

  return `
    <div class="panel-section">
      <h3>首尾帧素材库</h3>
      <p class="panel-section__tip">首尾帧素材独立于画面素材管理，适合沉淀片头、片尾、收束镜头等关键帧资源。</p>
    </div>
    <div class="panel-section">
      <div class="frame-stack">
        ${renderFrameCard("opening")}
        ${renderFrameCard("ending")}
      </div>
    </div>
  `;
}

function renderCharacterTab() {
  const groups = characterGroups();
  if (!groups.includes(state.characterGroup)) {
    state.characterGroup = groups[0] || "默认分组";
  }
  const query = state.searches.character.trim().toLowerCase();
  const list = materialsOf("characters")
    .filter((item) => (item.group_name || "默认分组") === state.characterGroup)
    .filter((item) => !query || `${item.name}${item.description || ""}`.toLowerCase().includes(query));
  const currentParsed = selectedParsedCharacter();
  const previewBlock = currentParsed?.preview_image_url
    ? `
      <div class="binding-preview-card">
        <div class="binding-preview-card__media"><img src="${currentParsed.preview_image_url}" alt="${currentParsed.name}" loading="lazy" /></div>
        <div class="binding-preview-card__body">
          <strong>角色预览已生成</strong>
          <span>${currentParsed.normalized_prompt || currentParsed.description || "可确认保存到角色素材库。"}</span>
          <div class="binding-preview-card__actions">
            <button class="btn btn--primary" type="button" data-character-preview-confirm="true">确认保存为角色素材</button>
            <button class="btn btn--ghost" type="button" data-character-preview-discard="true">取消预览</button>
          </div>
        </div>
      </div>
    `
    : "";
  const bindingSummary = state.characterBindingMode
    ? `
      <div class="panel-section">
        <div class="binding-toolbar">
          <div>
            <h3>正文角色绑定</h3>
            <p>从正文里的【角色列表】解析出角色，然后绑定已有素材或生成新角色图。</p>
          </div>
        </div>
        <div class="parsed-role-list">
          ${(state.parsedCharacters || []).map((item) => {
            const bound = materialsOf("characters").find((material) => material.id === item.bound_material_id);
            return `
              <button
                class="parsed-role-chip ${state.selectedParsedCharacterId === item.draft_character_id ? "is-active" : ""}"
                type="button"
                data-parsed-character-id="${item.draft_character_id}"
              >
                <strong>${item.name}</strong>
                <span>${bound ? `已绑定：${bound.name}` : item.preview_image_url ? "已有预览待确认" : "未绑定"}</span>
              </button>
            `;
          }).join("")}
        </div>
      </div>
      ${currentParsed ? `
        <div class="panel-section">
          <div class="binding-detail-card">
            <div class="binding-detail-card__head">
              <div>
                <h4>${currentParsed.name}</h4>
                <p>${currentParsed.description || "未填写角色描述。"}</p>
              </div>
              <span class="binding-status-chip binding-status-chip--${currentParsed.bound_material_id ? "done" : currentParsed.generation_status || "idle"}">${currentParsed.bound_material_id ? "已绑定" : currentParsed.generation_status === "generating" ? "生成中" : currentParsed.preview_image_url ? "待确认" : "未绑定"}</span>
            </div>
            <div class="binding-action-row">
              <div class="provider-field">
                <span>当前生图助手</span>
                <strong>${selectedImageAssistant()?.display_name || "暂无可用生图助手"}</strong>
              </div>
              <button class="btn btn--secondary" type="button" data-character-generate="true" ${availableCharacterImageAssistants.length ? "" : "disabled"}>${currentParsed.generation_status === "generating" ? "生成中..." : "生成新角色图"}</button>
              <button class="btn btn--ghost" type="button" data-character-unbind="true" ${currentParsed.bound_material_id ? "" : "disabled"}>清除绑定</button>
            </div>
            ${currentParsed.error ? `<p class="provider-card__error is-inline">${currentParsed.error}</p>` : ""}
            ${previewBlock}
          </div>
        </div>
      ` : ""}
    `
    : `
      <div class="panel-section">
        <div class="binding-empty">
          <h3>角色素材</h3>
          <p>正文里的角色不会自动绑定图片。点击顶部“角色绑定”后，可从右侧按角色逐个绑定已有素材或生成新角色图。</p>
        </div>
      </div>
    `;
  return `
    ${bindingSummary}
    <div class="panel-section">
      <h3>${state.characterBindingMode ? "绑定已有角色素材" : "角色素材列表"}</h3>
      <div class="segment-control">
        ${groups.map((group) => `
          <button class="${state.characterGroup === group ? "is-active" : ""}" data-character-group="${group}">${group}</button>
        `).join("")}
      </div>
    </div>
    <div class="panel-section">
      <input class="search-input" id="character_search" placeholder="搜索角色名称" value="${state.searches.character}" />
    </div>
    <div class="panel-section">
      <div class="character-grid">
        ${list.length ? list.map((item) => `
          <article class="character-card ${(state.characterBindingMode ? currentParsed?.bound_material_id === item.id : state.characterIds.includes(item.id)) ? "is-selected" : ""}" data-character-id="${item.id}">
            <div class="character-card__media character-card__media--image">
              ${item.image_url || item.public_url ? `<img src="${item.image_url || item.public_url}" alt="${item.name}" loading="lazy" />` : '<div class="character-card__placeholder">无预览</div>'}
            </div>
            <strong>${item.name}</strong>
            <span>${item.description || ""}</span>
          </article>
        `).join("") : '<div class="tasks-empty"><h3>该分组暂无角色</h3><p>先去配置中心为这个分组创建角色素材。</p></div>'}
      </div>
    </div>
  `;
}

function renderVoiceTab() {
  const query = state.searches.voice.trim().toLowerCase();
  const list = materialsOf("voices").filter((item) => !query || `${item.name}${item.tone || ""}${item.description || ""}`.toLowerCase().includes(query));
  return `
    <div class="panel-section">
      <h3>配音库</h3>
      <input class="search-input" id="voice_search" placeholder="搜索音色名称" value="${state.searches.voice}" />
    </div>
    <div class="voice-list">
      ${list.map((item) => `
        <article class="voice-item ${state.voiceId === item.id ? "is-selected" : ""}" data-voice-id="${item.id}">
          <div class="voice-item__meta">
            <strong>${item.name}</strong>
            <span>${item.tone || item.description || ""}</span>
          </div>
          ${audioPreview(item.audio_url)}
        </article>
      `).join("")}
    </div>
  `;
}

function renderMusicTab() {
  const query = state.searches.music.trim().toLowerCase();
  const list = materialsOf("music").filter((item) => !query || `${item.name}${item.author || ""}${item.genre_tags || ""}`.toLowerCase().includes(query));
  const bgmLabel = uploadFileNameLabel(state.bgmFile);
  return `
    <div class="panel-section">
      <h3>音乐素材库</h3>
      <input class="search-input" id="music_search" placeholder="搜索歌曲名称 / 歌手" value="${state.searches.music}" />
    </div>
    <div class="panel-section">
      <div class="setting-card upload-surface">
        <div class="upload-surface__head">
          <div>
            <label for="bgm">本地 BGM 文件</label>
            <p>上传后仅用于当前任务，不会自动写入音乐素材库。</p>
          </div>
        </div>
        <label class="upload-picker upload-picker--audio">
          <input id="bgm" class="upload-picker__input" type="file" accept="audio/*" />
          <span class="upload-picker__button">${state.bgmFile ? "替换文件" : "选择音频"}</span>
          <span class="upload-picker__meta">${state.bgmFile ? bgmLabel : "支持 MP3、WAV、M4A 等常见音频格式"}</span>
        </label>
      </div>
      <div class="setting-card" style="margin-top:10px;">
        <label for="bgm_volume">背景音乐音量</label>
        <input id="bgm_volume" type="number" value="${state.bgmVolume}" step="0.05" min="0" max="2" />
      </div>
    </div>
    <div class="music-list">
      ${list.map((item) => `
        <article class="music-item ${state.musicId === item.id ? "is-selected" : ""}" data-music-id="${item.id}">
          <div class="music-item__meta">
            <strong>${item.name}</strong>
            <span>${item.author || "未知作者"}${item.duration_ms ? ` · ${Math.round(item.duration_ms / 1000)}s` : ""}</span>
          </div>
          <span>${item.genre_tags || item.description || ""}</span>
          ${audioPreview(item.audio_url)}
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
    frames: renderFramesTab,
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
  renderStoryAssistantSelect();
  renderImageAssistantSelect();
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

async function generateDraft() {
  if (!availableStoryAssistants.length || !state.storyAssistantCode) {
    window.alert("请先在配置中心配置可用的故事助手。");
    return;
  }
  const prompt = $("assistant_prompt")?.value.trim() || "";
  if (!prompt) {
    window.alert("先输入你想创作的视频主题。");
    return;
  }
  const button = $("assistant_generate");
  if (button) {
    button.disabled = true;
    button.textContent = "生成中...";
  }
  setGlobalStatus("故事生成中", "running");
  if ($("job_hint")) $("job_hint").textContent = "正在调用故事助手生成策划与分镜草稿...";
  try {
    const style = styleById(state.visualStyleId);
    const draft = await generateStoryDraft({
      assistant_code: state.storyAssistantCode,
      prompt,
      aspect_ratio: state.aspectRatio || null,
      template_name: platformTemplates.find((item) => item.id === state.templateId)?.name || null,
      visual_style_name: style?.name || null,
      visual_style_prompt: style?.prompt_fragment || null,
      characters: charactersByIds(state.characterIds).map((item) => ({
        name: item.name,
        description: item.description || "",
      })),
    });
    state.assistantPrompt = prompt;
    state.storySummary = draft.story_summary;
    state.storyText = draft.story_text;
    state.scenes = (draft.scenes || []).map((scene) => ({
      title: scene.title || "",
      prompt: scene.prompt || "",
      subtitle: scene.subtitle || "",
      duration_s: Number(scene.duration_s || 4),
      characterIds: [...state.characterIds],
    }));
    mergeParsedCharacters(parseCharactersFromStoryText(draft.story_text || ""));
    state.activeSceneIndex = 0;
    setGlobalStatus("故事草稿已生成", "done");
    if ($("job_hint")) $("job_hint").textContent = "故事与分镜草稿已生成，可继续调整正文、分镜和右侧素材。";
    renderAll();
  } catch (error) {
    setGlobalStatus("故事生成失败", "error");
    if ($("job_hint")) $("job_hint").textContent = `故事生成失败：${error.message}`;
    window.alert(`故事生成失败：${error.message}`);
  } finally {
    if (button) {
      button.disabled = !availableStoryAssistants.length;
      button.textContent = availableStoryAssistants.length ? "生成故事与分镜" : "请先配置故事助手";
    }
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
    scene.characterIds = scene.characterIds || [];
    if (scene.characterIds.includes(id)) {
      scene.characterIds = scene.characterIds.filter((item) => item !== id);
    } else {
      scene.characterIds = [...scene.characterIds, id];
    }
  }
}

function buildStoryboardPayload() {
  const template = platformTemplates.find((item) => item.id === state.templateId) || null;
  const aspect = aspectDimensions(state.aspectRatio || inferAspectRatio(template?.width, template?.height));
  const style = styleById(state.visualStyleId);
  const storyText = $("story_document")?.value || state.storyText;
  const storySummary = documentSummary(storyText);
  const boundCharacterIds = [...new Set((state.parsedCharacters || []).map((item) => item.bound_material_id).filter(Boolean))];
  const effectiveCharacterIds = boundCharacterIds.length ? boundCharacterIds : [...state.characterIds];
  return {
    template_id: state.templateId || null,
    width: aspect.width,
    height: aspect.height,
    aspect_ratio: state.aspectRatio || inferAspectRatio(aspect.width, aspect.height),
    duration_s: state.scenes.reduce((sum, scene) => sum + Number(scene.duration_s || 0), 0) || (template ? template.duration_s : 15),
    scene_type: state.sceneType,
    story_summary: storySummary,
    story_text: storyText,
    visual_asset_id: state.visualStyleId || null,
    visual_style_id: state.visualStyleId || null,
    style_prompt: style?.prompt_fragment || "",
    opening_frame_asset_id: state.openingFrame.source_type === "library" ? state.openingFrame.asset_id || null : null,
    opening_frame_url: state.openingFrame.source_type === "generated" ? state.openingFrame.preview_url || null : null,
    ending_frame_asset_id: state.endingFrame.source_type === "library" ? state.endingFrame.asset_id || null : null,
    ending_frame_url: state.endingFrame.source_type === "generated" ? state.endingFrame.preview_url || null : null,
    character_ids: effectiveCharacterIds,
    voice_id: state.voiceId || null,
    music_id: state.musicId || null,
    style: style?.prompt_fragment || "",
    subtitles: state.subtitles,
    bgm_volume: Number(state.bgmVolume),
    scenes: state.scenes.map((scene) => ({
      duration_s: Number(scene.duration_s || 4),
      prompt: scene.prompt || "",
      subtitle: scene.subtitle || "",
      title: scene.title || "",
      visual_asset_id: scene.visual_asset_id || state.visualStyleId || null,
      character_ids: effectiveCharacterIds,
      character_prompt_fragments: charactersByIds(effectiveCharacterIds).map((item) => item.prompt_fragment).filter(Boolean),
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
  state.storyText = $("story_document")?.value || state.storyText;
  state.storySummary = documentSummary(state.storyText);
  if (!state.provider) {
    window.alert("当前没有可用视频助手。");
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
  if (state.openingFrame.source_type === "upload" && state.openingFrame.file) formData.append("opening_frame", state.openingFrame.file);
  if (state.endingFrame.source_type === "upload" && state.endingFrame.file) formData.append("ending_frame", state.endingFrame.file);

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

function syncMaterialSelections() {
  const visuals = materialsOf("visuals");
  const frames = materialsOf("frames");
  const characters = materialsOf("characters");
  const voices = materialsOf("voices");
  const music = materialsOf("music");
  const groups = [...new Set(characters.map((item) => item.group_name || "默认分组").filter(Boolean))];

  if (!state.visualStyleId || !visuals.some((item) => item.id === state.visualStyleId)) {
    state.visualStyleId = visuals[0]?.id || "";
  }
  state.characterIds = state.characterIds.filter((id) => characters.some((item) => item.id === id));
  if (!groups.includes(state.characterGroup)) {
    state.characterGroup = groups[0] || "默认分组";
  }
  if (!state.voiceId || !voices.some((item) => item.id === state.voiceId)) {
    state.voiceId = voices[0]?.id || "";
  }
  if (!state.musicId || !music.some((item) => item.id === state.musicId)) {
    state.musicId = music[0]?.id || "";
  }
  if (!state.characterImageAssistantCode || !availableCharacterImageAssistants.some((item) => item.assistant_code === state.characterImageAssistantCode)) {
    state.characterImageAssistantCode = availableCharacterImageAssistants[0]?.assistant_code || "";
  }
  if (state.openingFrame.source_type === "library" && state.openingFrame.asset_id && !frames.some((item) => item.id === state.openingFrame.asset_id)) {
    clearFrameState("opening");
  }
  if (state.endingFrame.source_type === "library" && state.endingFrame.asset_id && !frames.some((item) => item.id === state.endingFrame.asset_id)) {
    clearFrameState("ending");
  }
  state.parsedCharacters = (state.parsedCharacters || []).map((item) => {
    const stillExists = !item.bound_material_id || characters.some((material) => material.id === item.bound_material_id);
    return {
      ...item,
      bound_material_id: stillExists ? item.bound_material_id : "",
      generation_status: stillExists ? item.generation_status : "idle",
      error: stillExists ? item.error : "角色素材已失效，请重新确认绑定",
    };
  });
  syncCharacterIdsFromBindings();
}

function applyTemplateDefaults() {
  const template = platformTemplates.find((item) => item.id === state.templateId) || platformTemplates[0] || null;
  if (!template) return;
  state.templateId = template.id;
  state.aspectRatio = inferAspectRatio(template.width, template.height);
}

function attachStudioEvents() {
  $("assistant_generate")?.addEventListener("click", generateDraft);
  $("add_scene")?.addEventListener("click", addScene);
  $("submit")?.addEventListener("click", submitJob);
  $("character_binding_toggle")?.addEventListener("click", () => {
    parseAndOpenCharacterBinding();
  });
  $("frame_binding_toggle")?.addEventListener("click", openFrameBindingMode);

  document.addEventListener("click", (event) => {
    if (!pageIsStudio()) return;
    const target = event.target.closest("[data-tab], [data-style-id], [data-character-id], [data-character-group], [data-voice-id], [data-music-id], [data-voice-filter], [data-music-filter], [data-action], [data-parsed-character-id], [data-character-generate], [data-character-unbind], [data-character-preview-confirm], [data-character-preview-discard], [data-frame-generate], [data-frame-clear], .scene-card");
    if (!target) return;
    if (target.dataset.tab) {
      state.activeTab = target.dataset.tab;
      if (state.activeTab !== "character") state.characterBindingMode = false;
      if (state.activeTab !== "frames") state.frameBindingMode = false;
      renderResourcePanel();
      return;
    }
    if (target.dataset.styleId) {
      state.visualStyleId = target.dataset.styleId;
      renderAll();
      return;
    }
    if (target.dataset.characterGroup) {
      state.characterGroup = target.dataset.characterGroup;
      renderResourcePanel();
      return;
    }
    if (target.dataset.parsedCharacterId) {
      state.selectedParsedCharacterId = target.dataset.parsedCharacterId;
      renderResourcePanel();
      return;
    }
    if (target.dataset.characterId) {
      if (state.characterBindingMode && state.selectedParsedCharacterId) {
        setParsedCharacterBinding(state.selectedParsedCharacterId, target.dataset.characterId);
        return;
      }
      toggleCharacterSelection(target.dataset.characterId);
      renderAll();
      return;
    }
    if (target.dataset.characterGenerate) {
      generateSelectedCharacterPreview();
      return;
    }
    if (target.dataset.characterUnbind) {
      if (state.selectedParsedCharacterId) setParsedCharacterBinding(state.selectedParsedCharacterId, "");
      return;
    }
    if (target.dataset.characterPreviewConfirm) {
      confirmSelectedCharacterPreview();
      return;
    }
    if (target.dataset.characterPreviewDiscard) {
      discardSelectedCharacterPreview();
      return;
    }
    if (target.dataset.frameGenerate) {
      generateFramePreview(target.dataset.frameGenerate);
      return;
    }
    if (target.dataset.frameClear) {
      clearFrameSelection(target.dataset.frameClear);
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
    if (event.target.id === "story_document") {
      state.storyText = event.target.value;
      state.storySummary = documentSummary(state.storyText);
      const latestParsed = parseCharactersFromStoryText(state.storyText);
      const latestKeys = latestParsed.map((item) => item.draft_character_id).join("|");
      const currentKeys = (state.parsedCharacters || []).map((item) => item.draft_character_id).join("|");
      if (state.parsedCharacters.length && latestKeys !== currentKeys) {
        state.parsedCharacters = state.parsedCharacters.map((item) => ({
          ...item,
          error: "正文角色已变化，请重新点击“角色绑定”确认绑定",
        }));
      }
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
    if (event.target.id === "bgm_volume") state.bgmVolume = Number(event.target.value);
  });

  document.addEventListener("change", (event) => {
    if (!pageIsStudio()) return;
    if (event.target.id === "studio_provider") {
      if (event.target.value === "__config__") {
        navigateToConfigTab("providers");
        return;
      }
      state.provider = event.target.value;
      renderResourceNote();
    }
    if (event.target.id === "story_assistant_select") {
      if (event.target.value === "__config__") {
        navigateToConfigTab("assistants");
        return;
      }
      state.storyAssistantCode = event.target.value;
    }
    if (event.target.id === "image_assistant_select" || event.target.id === "character_image_assistant_select") {
      if (event.target.value === "__config__") {
        navigateToConfigTab("character-image-assistants");
        return;
      }
      state.characterImageAssistantCode = event.target.value;
      renderResourcePanel();
    }
    if (event.target.id === "aspect_ratio") {
      state.aspectRatio = event.target.value;
    }
    if (event.target.id === "template_id") {
      state.templateId = event.target.value;
      applyTemplateDefaults();
      renderResourcePanel();
    }
    if (event.target.id === "subtitles") {
      state.subtitles = event.target.checked;
    }
    if (event.target.id === "bgm") {
      state.bgmFile = event.target.files?.[0] || null;
    }
    if (event.target.dataset.frameSelect) {
      const type = event.target.dataset.frameSelect;
      if (!event.target.value) {
        clearFrameSelection(type);
      } else {
        selectFrameFromLibrary(type, event.target.value);
      }
    }
    if (event.target.dataset.frameSource) {
      setFrameSource(event.target.dataset.frameSource, event.target.value);
    }
    if (event.target.dataset.frameUpload) {
      setFrameUpload(event.target.dataset.frameUpload, event.target.files?.[0] || null);
    }
  });
}

async function initStudio() {
  setGlobalStatus("初始化中", "idle");
  try {
    const materials = await fetchMaterials();
    Object.assign(materialLibrary, materials);
    [platformTemplates, availableProviders, providerConfigs, availableStoryAssistants, availableCharacterImageAssistants] = await Promise.all([
      fetchPlatformTemplates(),
      fetchProviders(),
      fetchProviderConfigs(),
      fetchStoryAssistants(),
      fetchCharacterImageAssistants(),
    ]);
    state.templateId = platformTemplates[0]?.id || "";
    applyTemplateDefaults();
    state.provider = availableProviders[0]?.provider_code || "";
    state.storyAssistantCode = availableStoryAssistants[0]?.assistant_code || "";
    state.characterImageAssistantCode = availableCharacterImageAssistants[0]?.assistant_code || "";
    state.characterGroup = characterGroups()[0] || "默认分组";
    syncMaterialSelections();
    renderAll();
    attachStudioEvents();
    if (!availableProviders.length) {
      setGlobalStatus("暂无可用视频助手", "error");
      if ($("job_hint")) $("job_hint").textContent = "当前没有已启用且校验通过的视频助手。";
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
            <span>${job.provider_code || "未指定视频助手"}</span>
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
          <span>视频助手：${scene.provider_code}</span>
          <span>平台任务：${scene.provider_task_id || "未提交"}</span>
          <span>平台状态：${scene.provider_status || "未记录"}</span>
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
      taskMetric("视频助手", job.provider_code || "未记录"),
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

function providerDraft() {
  const draftId = globalThis.crypto?.randomUUID?.() || Math.random().toString(36).slice(2, 10);
  return {
    provider_code: `custom:${draftId}`,
    display_name: "未命名视频助手",
    enabled: false,
    sort_order: 100,
    description: "",
    config_version: 1,
    provider_config_json: { protocol: "openai", base_url: "", api_key: "", model: "" },
    is_valid: false,
    last_checked_at: null,
    last_error: "",
    capabilities: { supports_async_tasks: true, supports_scene_video: true },
    config_fields: [
      {
        key: "protocol",
        label: "协议类型",
        kind: "select",
        required: true,
        options: [
          { label: "OpenAI", value: "openai" },
          { label: "Anthropic", value: "anthropic" },
        ],
      },
      { key: "base_url", label: "URL", kind: "text", required: true, placeholder: "https://example.com/generate" },
      { key: "api_key", label: "API Key", kind: "password", required: true, placeholder: "" },
      { key: "model", label: "Model", kind: "text", required: true, placeholder: "video-model-v1" },
    ],
    is_custom: true,
    __draft: true,
  };
}

function renderProviderConfigCard(config) {
  const fields = config.config_fields || [];
  const credentials = fields.filter((field) => field.key === "app_key" || field.key === "app_secret");
  const requestFields = fields.filter((field) => field.key === "req_key" || field.key === "base_url");
  const statusText = config.is_valid ? "当前配置已校验，可作为工作区可选的视频助手。" : (config.last_error || "当前配置尚未通过校验。");
  const renderField = (field) => `
    <label class="provider-field">
      <span>${field.label}</span>
      ${field.kind === "checkbox"
        ? `<input type="checkbox" data-provider-field="${config.provider_code}:${field.key}" ${providerFieldValue(config, field) ? "checked" : ""} />`
        : field.kind === "select"
          ? `<select data-provider-field="${config.provider_code}:${field.key}">${(field.options || []).map((option) => `<option value="${option.value}" ${String(providerFieldValue(config, field)) === String(option.value) ? "selected" : ""}>${option.label}</option>`).join("")}</select>`
          : `<input type="${field.kind === "password" ? "password" : "text"}" data-provider-field="${config.provider_code}:${field.key}" value="${providerFieldValue(config, field)}" placeholder="${field.placeholder || ""}" ${field.required ? "required" : ""} />`}
      ${field.help_text ? `<small>${field.help_text}</small>` : ""}
    </label>
  `;
  if (config.is_custom) {
    return `
      <article class="provider-card provider-card--jimeng" data-provider-code="${config.provider_code}">
        <div class="provider-card__head">
          <div class="provider-card__title">
            <div class="provider-card__badge">自定义视频助手</div>
            <h3>${config.display_name || "未命名视频助手"}</h3>
            <p>${config.description || "通过自定义 URL / API Key / Model 调用外部视频生成服务。"}</p>
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
              <span>启用为工作区可选视频助手</span>
            </label>
            <div class="provider-card__meta">
              <span>助手标识：${config.provider_code}</span>
              <span>最近校验：${parseDate(config.last_checked_at)}</span>
            </div>
          </div>

          <section class="provider-section">
            <div class="provider-section__head">
              <strong>基础信息</strong>
              <span>用于区分不同自定义视频助手。</span>
            </div>
            <div class="provider-form provider-form--two-col">
              <label class="provider-field">
                <span>名称</span>
                <input type="text" data-provider-meta="${config.provider_code}:display_name" value="${config.display_name || ""}" />
              </label>
              <label class="provider-field">
                <span>排序</span>
                <input type="number" data-provider-meta="${config.provider_code}:sort_order" value="${config.sort_order ?? 100}" />
              </label>
              <label class="provider-field provider-field--full">
                <span>描述</span>
                <input type="text" data-provider-meta="${config.provider_code}:description" value="${config.description || ""}" />
              </label>
            </div>
          </section>

          <section class="provider-section">
            <div class="provider-section__head">
              <strong>模型连接</strong>
              <span>接口需同步返回 JSON，至少包含 video_url 字段。</span>
            </div>
            <div class="provider-form provider-form--two-col">
              ${fields.map(renderField).join("")}
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
  return `
    <article class="provider-card provider-card--jimeng" data-provider-code="${config.provider_code}">
      <div class="provider-card__head">
        <div class="provider-card__title">
          <div class="provider-card__badge">视频助手</div>
          <h3>${config.display_name}</h3>
          <p>${config.description || "管理该视频助手的凭证、默认请求参数与启用状态。"}</p>
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
            <span>启用为工作区可选视频助手</span>
          </label>
          <div class="provider-card__meta">
            <span>助手标识：${config.provider_code}</span>
            <span>最近校验：${parseDate(config.last_checked_at)}</span>
          </div>
        </div>

        <section class="provider-section">
          <div class="provider-section__head">
            <strong>基础凭证</strong>
            <span>用于保存该视频助手的账号鉴权信息</span>
          </div>
          <div class="provider-form provider-form--two-col">
            ${credentials.map(renderField).join("")}
          </div>
        </section>

        <section class="provider-section">
          <div class="provider-section__head">
            <strong>请求参数</strong>
            <span>用于管理默认 req_key 和接口访问地址</span>
          </div>
          <div class="provider-form provider-form--two-col">
            ${requestFields.map(renderField).join("")}
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
  if (activeConfigTab !== "providers") {
    list.innerHTML = "";
    return;
  }
  const visibleConfigs = [...pendingCustomProviderDrafts, ...providerConfigs].filter((item) => item.provider_code === activeConfigSection);
  if (!visibleConfigs.length) {
    list.innerHTML = `
      <div class="tasks-board__head tasks-board__head--compact">
        <div>
          <strong>视频助手</strong>
          <p>管理内置视频助手与自定义视频生成服务。</p>
        </div>
        <button class="btn btn--primary" type="button" data-provider-create="true">新增</button>
      </div>
      <div class="tasks-empty"><h3>暂无视频助手定义</h3><p>点击新增，创建一个自定义视频助手。</p></div>
    `;
    return;
  }
  list.innerHTML = `
    <div class="tasks-board__head tasks-board__head--compact">
      <div>
        <strong>视频助手</strong>
        <p>管理内置视频助手与自定义视频生成服务。</p>
      </div>
      <button class="btn btn--primary" type="button" data-provider-create="true">新增</button>
    </div>
    ${visibleConfigs.map(renderProviderConfigCard).join("")}
  `;
}

function storyAssistantDraft() {
  const draftId = globalThis.crypto?.randomUUID?.() || Math.random().toString(36).slice(2, 10);
  return {
    id: `draft-story-assistant-${draftId}`,
    assistant_code: "",
    display_name: "未命名故事助手",
    enabled: false,
    sort_order: 100,
    description: "",
    protocol: "openai",
    base_url: "",
    api_key: "",
    model: "",
    system_prompt: "",
    temperature: 0.7,
    is_valid: false,
    last_checked_at: null,
    last_error: "",
    __draft: true,
  };
}

function renderStoryAssistantCard(config) {
  const prefix = config.__draft ? config.id : config.assistant_code;
  return `
    <article class="provider-card" data-story-assistant-code="${prefix}">
      <div class="provider-card__head">
        <div class="provider-card__title">
          <div class="provider-card__badge">故事助手</div>
          <h3>${config.display_name || "未命名故事助手"}</h3>
          <p>${config.description || "负责生成故事概览、策划正文与分镜草稿，支持 OpenAI 或 Anthropic 协议。"}</p>
        </div>
        <div class="provider-card__status">
          <span class="task-card__badge task-card__badge--${config.is_valid ? "done" : "error"}">${config.is_valid ? "已校验" : "待配置"}</span>
          <span class="provider-card__status-text">${config.last_error || "配置完成后可在工作台中选择这个故事助手。"}</span>
        </div>
      </div>
      <div class="provider-card__surface">
        <div class="provider-card__row">
          <label class="setting-toggle provider-card__toggle">
            <input type="checkbox" data-story-assistant-field="${prefix}:enabled" ${config.enabled ? "checked" : ""} />
            <span>启用为工作台可选故事助手</span>
          </label>
          <div class="provider-card__meta">
            <span>Assistant Code：${config.assistant_code || "待填写"}</span>
            <span>最近校验：${parseDate(config.last_checked_at)}</span>
          </div>
        </div>

        <section class="provider-section">
          <div class="provider-section__head">
            <strong>基础信息</strong>
            <span>用于区分不同故事助手与排序。</span>
          </div>
          <div class="provider-form provider-form--two-col">
            <label class="provider-field">
              <span>助手标识</span>
              <input type="text" data-story-assistant-field="${prefix}:assistant_code" value="${config.assistant_code || ""}" placeholder="例如：openai-story" ${config.__draft ? "" : "readonly"} />
            </label>
            <label class="provider-field">
              <span>名称</span>
              <input type="text" data-story-assistant-field="${prefix}:display_name" value="${config.display_name || ""}" />
            </label>
            <label class="provider-field">
              <span>描述</span>
              <input type="text" data-story-assistant-field="${prefix}:description" value="${config.description || ""}" />
            </label>
            <label class="provider-field">
              <span>排序</span>
              <input type="number" data-story-assistant-field="${prefix}:sort_order" value="${config.sort_order ?? 100}" />
            </label>
            <label class="provider-field">
              <span>协议</span>
              <select data-story-assistant-field="${prefix}:protocol">
                <option value="openai" ${((config.protocol || "openai") === "openai") ? "selected" : ""}>OpenAI</option>
                <option value="anthropic" ${((config.protocol || "openai") === "anthropic") ? "selected" : ""}>Anthropic</option>
              </select>
            </label>
          </div>
        </section>

        <section class="provider-section">
          <div class="provider-section__head">
            <strong>模型连接</strong>
            <span>按所选协议填写 Base URL、API Key 和模型名。Anthropic 使用 Messages API。</span>
          </div>
          <div class="provider-form provider-form--two-col">
            <label class="provider-field">
              <span>Base URL</span>
              <input type="text" data-story-assistant-field="${prefix}:base_url" value="${config.base_url || ""}" placeholder="${(config.protocol || "openai") === "anthropic" ? "https://api.anthropic.com/v1" : "https://api.openai.com/v1"}" />
            </label>
            <label class="provider-field">
              <span>Model</span>
              <input type="text" data-story-assistant-field="${prefix}:model" value="${config.model || ""}" placeholder="${(config.protocol || "openai") === "anthropic" ? "claude-sonnet-4-5" : "gpt-4o-mini"}" />
            </label>
            <label class="provider-field">
              <span>API Key</span>
              <input type="password" data-story-assistant-field="${prefix}:api_key" value="${config.api_key || ""}" />
            </label>
            <label class="provider-field">
              <span>Temperature</span>
              <input type="number" step="0.1" min="0" max="2" data-story-assistant-field="${prefix}:temperature" value="${config.temperature ?? 0.7}" />
            </label>
          </div>
        </section>

        <section class="provider-section">
          <div class="provider-section__head">
            <strong>系统提示词</strong>
            <span>不填写时使用后端默认故事策划提示词。</span>
          </div>
          <div class="provider-form provider-form--single">
            <label class="provider-field">
              <span>System Prompt</span>
              <textarea rows="8" data-story-assistant-field="${prefix}:system_prompt">${config.system_prompt || ""}</textarea>
            </label>
          </div>
        </section>
      </div>
      <div class="provider-card__actions">
        <button class="btn btn--ghost" type="button" data-story-assistant-validate="${prefix}:${config.__draft ? "draft" : "persisted"}">校验配置</button>
        <button class="btn btn--primary" type="button" data-story-assistant-save="${prefix}:${config.__draft ? "draft" : "persisted"}">保存配置</button>
      </div>
      <p class="provider-card__error" id="story_assistant_error_${prefix}">${config.last_error || ""}</p>
    </article>
  `;
}

function renderStoryAssistantsPage() {
  const list = $("providers_list");
  if (!list) return;
  if (activeConfigTab !== "assistants") {
    list.innerHTML = "";
    return;
  }
  const sidebarItems = [
    ...pendingStoryAssistantDrafts.map((item) => ({ ...item, __draft: true })),
    ...storyAssistantConfigs,
  ];
  if (!sidebarItems.length) {
    list.innerHTML = `
      <div class="tasks-board__head tasks-board__head--compact">
        <div>
          <strong>故事助手</strong>
          <p>为工作台配置一个或多个大模型故事助手。</p>
        </div>
        <button class="btn btn--primary" type="button" data-story-assistant-create="true">新增</button>
      </div>
      <div class="tasks-empty"><h3>暂无故事助手</h3><p>点击新增，填写一个 OpenAI 兼容模型配置。</p></div>
    `;
    return;
  }
  const visible = sidebarItems.filter((item) => (item.__draft ? item.id : item.assistant_code) === activeConfigSection);
  list.innerHTML = `
    <div class="tasks-board__head tasks-board__head--compact">
      <div>
        <strong>故事助手</strong>
        <p>工作台左侧“生成故事与分镜”按钮会调用这里启用并校验通过的助手。</p>
      </div>
      <button class="btn btn--primary" type="button" data-story-assistant-create="true">新增</button>
    </div>
    ${visible.map(renderStoryAssistantCard).join("")}
  `;
}

function characterImageAssistantDraft() {
  const draftId = globalThis.crypto?.randomUUID?.() || Math.random().toString(36).slice(2, 10);
  return {
    id: `draft-character-image-assistant-${draftId}`,
    assistant_code: "",
    display_name: "未命名生图助手",
    enabled: false,
    sort_order: 100,
    description: "",
    protocol: "openai",
    base_url: "",
    api_key: "",
    model: "",
    system_prompt: "",
    is_valid: false,
    last_checked_at: null,
    last_error: "",
    __draft: true,
  };
}

function renderCharacterImageAssistantCard(config) {
  const prefix = config.__draft ? config.id : config.assistant_code;
  return `
    <article class="provider-card" data-character-image-assistant-code="${prefix}">
      <div class="provider-card__head">
        <div class="provider-card__title">
          <div class="provider-card__badge">生图助手</div>
          <h3>${config.display_name || "未命名生图助手"}</h3>
          <p>${config.description || "负责生成角色图、首帧图和尾帧图预览，并在需要时保存为角色素材。"}</p>
        </div>
        <div class="provider-card__status">
          <span class="task-card__badge task-card__badge--${config.is_valid ? "done" : "error"}">${config.is_valid ? "已校验" : "待配置"}</span>
          <span class="provider-card__status-text">${config.last_error || "配置完成后可在工作台的角色绑定或收尾帧流程中选择该助手。"}</span>
        </div>
      </div>
      <div class="provider-card__surface">
        <div class="provider-card__row">
          <label class="setting-toggle provider-card__toggle">
            <input type="checkbox" data-character-image-assistant-field="${prefix}:enabled" ${config.enabled ? "checked" : ""} />
            <span>启用为工作台可选生图助手</span>
          </label>
          <div class="provider-card__meta">
            <span>Assistant Code：${config.assistant_code || "待填写"}</span>
            <span>最近校验：${parseDate(config.last_checked_at)}</span>
          </div>
        </div>

        <section class="provider-section">
          <div class="provider-section__head">
            <strong>基础信息</strong>
            <span>用于区分不同生图助手与排序。</span>
          </div>
          <div class="provider-form provider-form--two-col">
            <label class="provider-field">
              <span>助手标识</span>
              <input type="text" data-character-image-assistant-field="${prefix}:assistant_code" value="${config.assistant_code || ""}" placeholder="例如：character-image-openai" ${config.__draft ? "" : "readonly"} />
            </label>
            <label class="provider-field">
              <span>名称</span>
              <input type="text" data-character-image-assistant-field="${prefix}:display_name" value="${config.display_name || ""}" />
            </label>
            <label class="provider-field">
              <span>描述</span>
              <input type="text" data-character-image-assistant-field="${prefix}:description" value="${config.description || ""}" />
            </label>
            <label class="provider-field">
              <span>排序</span>
              <input type="number" data-character-image-assistant-field="${prefix}:sort_order" value="${config.sort_order ?? 100}" />
            </label>
            <label class="provider-field">
              <span>协议</span>
              <select data-character-image-assistant-field="${prefix}:protocol">
                <option value="openai" ${((config.protocol || "openai") === "openai") ? "selected" : ""}>OpenAI</option>
                <option value="anthropic" ${((config.protocol || "openai") === "anthropic") ? "selected" : ""}>Anthropic</option>
              </select>
            </label>
          </div>
        </section>

        <section class="provider-section">
          <div class="provider-section__head">
            <strong>模型连接</strong>
            <span>生图服务需最终返回预览图地址或 base64 图片，供工作台预览和绑定使用。</span>
          </div>
          <div class="provider-form provider-form--two-col">
            <label class="provider-field">
              <span>Base URL</span>
              <input type="text" data-character-image-assistant-field="${prefix}:base_url" value="${config.base_url || ""}" placeholder="${(config.protocol || "openai") === "anthropic" ? "https://api.anthropic.com/v1" : "https://api.openai.com/v1"}" />
            </label>
            <label class="provider-field">
              <span>Model</span>
              <input type="text" data-character-image-assistant-field="${prefix}:model" value="${config.model || ""}" placeholder="${(config.protocol || "openai") === "anthropic" ? "claude-sonnet-4-5" : "gpt-image-1"}" />
            </label>
            <label class="provider-field">
              <span>API Key</span>
              <input type="password" data-character-image-assistant-field="${prefix}:api_key" value="${config.api_key || ""}" />
            </label>
          </div>
        </section>

        <section class="provider-section">
          <div class="provider-section__head">
            <strong>系统提示词</strong>
            <span>不填写时使用后端默认生图提示词。</span>
          </div>
          <div class="provider-form provider-form--single">
            <label class="provider-field">
              <span>System Prompt</span>
              <textarea rows="6" data-character-image-assistant-field="${prefix}:system_prompt">${config.system_prompt || ""}</textarea>
            </label>
          </div>
        </section>
      </div>
      <div class="provider-card__actions">
        <button class="btn btn--ghost" type="button" data-character-image-assistant-validate="${prefix}:${config.__draft ? "draft" : "persisted"}">校验配置</button>
        <button class="btn btn--primary" type="button" data-character-image-assistant-save="${prefix}:${config.__draft ? "draft" : "persisted"}">保存配置</button>
      </div>
      <p class="provider-card__error" id="character_image_assistant_error_${prefix}">${config.last_error || ""}</p>
    </article>
  `;
}

function renderCharacterImageAssistantsPage() {
  const list = $("providers_list");
  if (!list) return;
  if (activeConfigTab !== "character-image-assistants") {
    list.innerHTML = "";
    return;
  }
  const sidebarItems = [
    ...pendingCharacterImageAssistantDrafts.map((item) => ({ ...item, __draft: true })),
    ...characterImageAssistantConfigs,
  ];
  if (!sidebarItems.length) {
    list.innerHTML = `
      <div class="tasks-board__head tasks-board__head--compact">
        <div>
          <strong>生图助手</strong>
          <p>为工作台配置一个或多个统一的图片生成助手。</p>
        </div>
        <button class="btn btn--primary" type="button" data-character-image-assistant-create="true">新增</button>
      </div>
      <div class="tasks-empty"><h3>暂无生图助手</h3><p>点击新增，填写一个可返回图片预览的配置。</p></div>
    `;
    return;
  }
  const visible = sidebarItems.filter((item) => (item.__draft ? item.id : item.assistant_code) === activeConfigSection);
  list.innerHTML = `
    <div class="tasks-board__head tasks-board__head--compact">
      <div>
        <strong>生图助手</strong>
        <p>工作台中的角色图、首帧图和尾帧图生成都会调用这里启用并校验通过的助手。</p>
      </div>
      <button class="btn btn--primary" type="button" data-character-image-assistant-create="true">新增</button>
    </div>
    ${visible.map(renderCharacterImageAssistantCard).join("")}
  `;
}

function materialTypeLabel(type) {
  return {
    visuals: "画面素材",
    frames: "首尾帧素材",
    characters: "角色素材",
    voices: "配音素材",
    music: "音乐素材",
  }[type] || type;
}

function materialDraft(type) {
  const draftId = globalThis.crypto?.randomUUID?.() || Math.random().toString(36).slice(2, 10);
  const base = { id: `draft-${draftId}`, name: "未命名素材", description: "", prompt_fragment: "", enabled: true, sort_order: 100, __draft: true };
  if (type === "visuals") return { ...base };
  if (type === "frames") return { ...base };
  if (type === "characters") return { ...base, group_name: "默认分组" };
  if (type === "voices") return { ...base, tone: "" };
  return { ...base, author: "", genre_tags: "" };
}

function materialFileAccept(type) {
  return type === "visuals" || type === "frames" || type === "characters" ? "image/*" : "audio/*";
}

function renderMaterialPreview(type, item, prefix) {
  const localPreview = materialPreviewUrls.get(prefix);
  if (localPreview) return imageThumb(localPreview, item.name);
  if (type === "visuals") return imageThumb(item.cover_url || item.public_url, item.name);
  if (type === "frames") return imageThumb(item.cover_url || item.public_url, item.name);
  if (type === "characters") return imageThumb(item.image_url || item.public_url, item.name);
  return audioPreview(item.audio_url || item.public_url);
}

function renderMaterialFields(type, item, prefix) {
  const fileLabel = uploadedMaterialFileName(prefix);
  const fields = [
    (type === "visuals" || type === "frames" || type === "characters")
      ? `
        <div class="material-upload-card">
          <div class="material-upload-card__preview">
            ${renderMaterialPreview(type, item, prefix)}
          </div>
          <div class="material-upload-card__body">
            <div class="material-upload-card__text">
              <strong>${type === "visuals" ? "画面预览" : type === "frames" ? "首尾帧预览" : "角色预览"}</strong>
              <span>${fileLabel ? `已选择 ${fileNameLabel(fileLabel)}` : "选择图片后会立即在这里预览，保存后写入素材库。"}</span>
            </div>
            <div class="material-upload-card__actions">
              <label class="btn btn--secondary material-upload-card__button">
                <span>${fileLabel ? "替换图片" : "选择图片"}</span>
                <input class="material-upload-card__input" type="file" accept="${materialFileAccept(type)}" data-material-file="${prefix}" />
              </label>
              <button class="btn btn--ghost" type="button" data-material-clear-file="${prefix}" ${fileLabel ? "" : "aria-disabled=\"true\""}>清除</button>
            </div>
          </div>
        </div>
      `
      : `<div class="material-asset-preview">${renderMaterialPreview(type, item, prefix)}</div>`,
    `
      <label class="provider-field">
        <span>名称</span>
        <input type="text" data-material-field="${prefix}:name" value="${item.name || ""}" />
      </label>
    `,
    `
      <label class="provider-field">
        <span>描述</span>
        <input type="text" data-material-field="${prefix}:description" value="${item.description || ""}" />
      </label>
    `,
    `
      <label class="provider-field">
        <span>Prompt 片段</span>
        <input type="text" data-material-field="${prefix}:prompt_fragment" value="${item.prompt_fragment || ""}" />
      </label>
    `,
    `
      <label class="provider-field">
        <span>${type === "visuals" || type === "frames" || type === "characters" ? "素材说明" : "上传音频"}</span>
        ${type === "visuals" || type === "frames" || type === "characters"
          ? `<small>支持 PNG、JPG、WEBP 等常见图片格式，可多次替换，保存后生效。</small>`
          : `<input type="file" accept="${materialFileAccept(type)}" data-material-file="${prefix}" />`}
      </label>
    `,
    `
      <label class="provider-field">
        <span>排序</span>
        <input type="number" data-material-field="${prefix}:sort_order" value="${item.sort_order || 100}" />
      </label>
    `,
  ];
  if (type === "characters") {
    fields.push(`
      <label class="provider-field">
        <span>分组</span>
        <input type="text" data-material-field="${prefix}:group_name" value="${item.group_name || "默认分组"}" placeholder="例如：默认分组 / 主角 / 配角 / 宠物" />
      </label>
    `);
  }
  if (type === "voices") {
    fields.push(`
      <label class="provider-field">
        <span>音色标签</span>
        <input type="text" data-material-field="${prefix}:tone" value="${item.tone || ""}" />
      </label>
    `);
  }
  if (type === "music") {
    fields.push(`
      <label class="provider-field">
        <span>作者</span>
        <input type="text" data-material-field="${prefix}:author" value="${item.author || ""}" />
      </label>
    `);
    fields.push(`
      <label class="provider-field">
        <span>风格标签</span>
        <input type="text" data-material-field="${prefix}:genre_tags" value="${item.genre_tags || ""}" />
      </label>
    `);
  }
  fields.push(`
    <label class="setting-toggle provider-card__toggle">
      <input type="checkbox" data-material-field="${prefix}:enabled" ${item.enabled ? "checked" : ""} />
      <span>启用</span>
    </label>
  `);
  return fields.join("");
}

function renderMaterialConfigPanel() {
  const panel = $("materials_config_panel");
  if (!panel) return;
  if (activeConfigTab !== "materials") {
    panel.innerHTML = "";
    return;
  }
  const items = [...(pendingMaterialDrafts[activeConfigSection] || []), ...(materialConfigs[activeConfigSection] || [])];
  panel.innerHTML = `
    <div class="tasks-board__head tasks-board__head--compact">
      <div>
        <strong>${materialTypeLabel(activeConfigSection)}</strong>
        <p>工作台中的候选项直接读取这里保存的数据。</p>
      </div>
      <button class="btn btn--primary" type="button" data-material-create="${activeConfigSection}">新增</button>
    </div>
    <div class="materials-config-list">
      ${items.length ? items.map((item) => `
        <article class="provider-card provider-card--material">
          <div class="provider-card__head">
            <div class="provider-card__title">
              <div class="provider-card__badge">${materialTypeLabel(activeConfigSection)}</div>
              <h3>${item.name}</h3>
              <p>${item.description || "未填写描述"}</p>
            </div>
          </div>
          <div class="provider-card__surface">
            <div class="provider-form provider-form--two-col">
              ${renderMaterialFields(activeConfigSection, item, `${activeConfigSection}:${item.id}`)}
            </div>
          </div>
          <div class="provider-card__actions">
            <button class="btn btn--ghost" type="button" data-material-save="${activeConfigSection}:${item.id}:${item.__draft ? "draft" : "persisted"}">${item.__draft ? "创建素材" : "保存"}</button>
            <button class="btn btn--danger" type="button" data-material-delete="${activeConfigSection}:${item.id}:${item.__draft ? "draft" : "persisted"}">删除</button>
          </div>
          <p class="provider-card__error" id="material_error_${activeConfigSection}_${item.id}"></p>
        </article>
      `).join("") : '<div class="tasks-empty"><h3>暂无素材</h3><p>点击新增，创建可供工作台选择的素材项。</p></div>'}
    </div>
  `;
}

function renderConfigSidebar() {
  const nav = $("config_sidebar_nav");
  const title = $("config_sidebar_title");
  if (!nav || !title) return;
  const items = activeConfigTab === "providers"
    ? [
        ...pendingCustomProviderDrafts.map((item) => ({ id: item.provider_code, label: item.display_name || "新增视频助手" })),
        ...providerConfigs.map((item) => ({ id: item.provider_code, label: item.display_name })),
      ]
    : activeConfigTab === "assistants"
      ? [
          ...pendingStoryAssistantDrafts.map((item) => ({ id: item.id, label: item.display_name || "新增故事助手" })),
          ...storyAssistantConfigs.map((item) => ({ id: item.assistant_code, label: item.display_name })),
        ]
      : activeConfigTab === "character-image-assistants"
        ? [
            ...pendingCharacterImageAssistantDrafts.map((item) => ({ id: item.id, label: item.display_name || "新增生图助手" })),
            ...characterImageAssistantConfigs.map((item) => ({ id: item.assistant_code, label: item.display_name })),
          ]
      : [
        { id: "visuals", label: "画面" },
        { id: "frames", label: "首尾帧" },
        { id: "characters", label: "角色" },
        { id: "voices", label: "配音" },
        { id: "music", label: "音乐" },
      ];
  title.textContent = activeConfigTab === "providers"
    ? "视频助手"
    : activeConfigTab === "assistants"
      ? "故事助手"
      : activeConfigTab === "character-image-assistants"
        ? "生图助手"
        : "素材配置";
  nav.innerHTML = items.map((item) => `
    <button
      class="settings-sidebar__item ${activeConfigSection === item.id ? "is-active" : ""}"
      data-config-section="${item.id}"
      type="button"
    >
      ${item.label}
    </button>
  `).join("");
}

function renderConfigPanels() {
  const providersList = $("providers_list");
  const materialsPanel = $("materials_config_panel");
  const title = $("config_content_title");
  const description = $("config_content_description");
  const providersRefresh = $("providers_refresh");
  const storyAssistantsRefresh = $("story_assistants_refresh");
  const characterImageAssistantsRefresh = $("character_image_assistants_refresh");
  const materialsRefresh = $("materials_refresh");
  if (!providersList || !materialsPanel || !title || !description) return;

  document.querySelectorAll(".settings-primary-tab").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.configTab === activeConfigTab);
  });

  renderConfigSidebar();

  if (activeConfigTab === "providers") {
    if (![...pendingCustomProviderDrafts.map((item) => item.provider_code), ...providerConfigs.map((item) => item.provider_code)].includes(activeConfigSection)) {
      activeConfigSection = pendingCustomProviderDrafts[0]?.provider_code || providerConfigs[0]?.provider_code || "jimeng";
    }
    providersList.hidden = false;
    materialsPanel.hidden = true;
    materialsPanel.innerHTML = "";
    if (providersRefresh) providersRefresh.hidden = false;
    if (storyAssistantsRefresh) storyAssistantsRefresh.hidden = true;
    if (characterImageAssistantsRefresh) characterImageAssistantsRefresh.hidden = true;
    if (materialsRefresh) materialsRefresh.hidden = true;
    title.textContent = "视频助手";
    description.textContent = "管理视频生成能力的启用状态、鉴权信息与默认请求参数。";
    renderProvidersPage();
    return;
  }

  if (activeConfigTab === "assistants") {
    if (![...pendingStoryAssistantDrafts.map((item) => item.id), ...storyAssistantConfigs.map((item) => item.assistant_code)].includes(activeConfigSection)) {
      activeConfigSection = pendingStoryAssistantDrafts[0]?.id || storyAssistantConfigs[0]?.assistant_code || "";
    }
    providersList.hidden = false;
    materialsPanel.hidden = true;
    materialsPanel.innerHTML = "";
    if (providersRefresh) providersRefresh.hidden = true;
    if (storyAssistantsRefresh) storyAssistantsRefresh.hidden = false;
    if (characterImageAssistantsRefresh) characterImageAssistantsRefresh.hidden = true;
    if (materialsRefresh) materialsRefresh.hidden = true;
    title.textContent = "故事助手";
    description.textContent = "配置工作台用于生成故事与分镜的大模型助手，支持多个 OpenAI 兼容模型并在工作台切换。";
    renderStoryAssistantsPage();
    return;
  }

  if (activeConfigTab === "character-image-assistants") {
    if (![...pendingCharacterImageAssistantDrafts.map((item) => item.id), ...characterImageAssistantConfigs.map((item) => item.assistant_code)].includes(activeConfigSection)) {
      activeConfigSection = pendingCharacterImageAssistantDrafts[0]?.id || characterImageAssistantConfigs[0]?.assistant_code || "";
    }
    providersList.hidden = false;
    materialsPanel.hidden = true;
    materialsPanel.innerHTML = "";
    if (providersRefresh) providersRefresh.hidden = true;
    if (storyAssistantsRefresh) storyAssistantsRefresh.hidden = true;
    if (characterImageAssistantsRefresh) characterImageAssistantsRefresh.hidden = false;
    if (materialsRefresh) materialsRefresh.hidden = true;
    title.textContent = "生图助手";
    description.textContent = "配置统一的图片生成模型，供工作台角色图、首帧图和尾帧图流程调用。";
    renderCharacterImageAssistantsPage();
    return;
  }

  if (!["visuals", "frames", "characters", "voices", "music"].includes(activeConfigSection)) {
    activeConfigSection = "visuals";
  }
  providersList.hidden = true;
  materialsPanel.hidden = false;
  providersList.innerHTML = "";
  if (providersRefresh) providersRefresh.hidden = true;
  if (storyAssistantsRefresh) storyAssistantsRefresh.hidden = true;
  if (characterImageAssistantsRefresh) characterImageAssistantsRefresh.hidden = true;
  if (materialsRefresh) materialsRefresh.hidden = false;
  title.textContent = materialTypeLabel(activeConfigSection);
  description.textContent = "维护工作区使用的素材定义。工作区只负责选择，配置在这里集中完成。";
  renderMaterialConfigPanel();
}

function collectProviderForm(providerCode) {
  const config = [...pendingCustomProviderDrafts, ...providerConfigs].find((item) => item.provider_code === providerCode);
  if (!config) return { enabled: false, provider_config_json: {} };
  const payload = {};
  (config.config_fields || []).forEach((field) => {
    const node = document.querySelector(`[data-provider-field="${providerCode}:${field.key}"]`);
    if (!node) return;
    payload[field.key] = field.kind === "checkbox" ? node.checked : node.value.trim();
  });
  const enabledNode = document.querySelector(`[data-provider-toggle="${providerCode}"]`);
  const displayNameNode = document.querySelector(`[data-provider-meta="${providerCode}:display_name"]`);
  const descriptionNode = document.querySelector(`[data-provider-meta="${providerCode}:description"]`);
  const sortOrderNode = document.querySelector(`[data-provider-meta="${providerCode}:sort_order"]`);
  return {
    enabled: Boolean(enabledNode?.checked),
    display_name: displayNameNode?.value.trim() || config.display_name,
    description: descriptionNode?.value.trim() || config.description || "",
    sort_order: sortOrderNode ? Number(sortOrderNode.value || 100) : config.sort_order,
    provider_config_json: payload,
  };
}

async function loadProviderConfigsIntoState() {
  providerConfigs = await fetchProviderConfigs();
  availableProviders = await fetchProviders();
}

async function loadStoryAssistantConfigsIntoState() {
  storyAssistantConfigs = await fetchStoryAssistantConfigs();
  availableStoryAssistants = await fetchStoryAssistants();
}

async function loadCharacterImageAssistantConfigsIntoState() {
  characterImageAssistantConfigs = await fetchCharacterImageAssistantConfigs();
  availableCharacterImageAssistants = await fetchCharacterImageAssistants();
}

function collectStoryAssistantForm(prefix) {
  const payload = {};
  document.querySelectorAll(`[data-story-assistant-field^="${prefix}:"]`).forEach((node) => {
    const field = node.dataset.storyAssistantField.split(":").slice(1).join(":");
    payload[field] = node.type === "checkbox" ? node.checked : node.value.trim();
  });
  payload.sort_order = Number(payload.sort_order || 100);
  payload.temperature = Number(payload.temperature ?? 0.7);
  return payload;
}

function collectCharacterImageAssistantForm(prefix) {
  const payload = {};
  document.querySelectorAll(`[data-character-image-assistant-field^="${prefix}:"]`).forEach((node) => {
    const field = node.dataset.characterImageAssistantField.split(":").slice(1).join(":");
    payload[field] = node.type === "checkbox" ? node.checked : node.value.trim();
  });
  payload.sort_order = Number(payload.sort_order || 100);
  return payload;
}

function collectMaterialForm(type, id) {
  const payload = {};
  document.querySelectorAll(`[data-material-field^="${type}:${id}:"]`).forEach((node) => {
    const field = node.dataset.materialField.split(":").slice(2).join(":");
    payload[field] = node.type === "checkbox" ? node.checked : node.value.trim();
  });
  payload.sort_order = Number(payload.sort_order || 100);
  if (type === "characters") payload.group_name = payload.group_name || "默认分组";
  return payload;
}

function collectMaterialFile(type, id) {
  return uploadedMaterialFile(materialDraftKey(type, id));
}

async function initConfigCenter() {
  try {
    await loadProviderConfigsIntoState();
    await loadStoryAssistantConfigsIntoState();
    await loadCharacterImageAssistantConfigsIntoState();
    materialConfigs = await fetchMaterialConfigs();
    const params = new URLSearchParams(window.location.search);
    const requestedTab = params.get("tab");
    activeConfigTab = ["providers", "assistants", "character-image-assistants", "materials"].includes(requestedTab || "")
      ? requestedTab
      : "providers";
    activeConfigSection = activeConfigTab === "providers"
      ? (providerConfigs[0]?.provider_code || "jimeng")
      : activeConfigTab === "assistants"
        ? (storyAssistantConfigs[0]?.assistant_code || "")
        : activeConfigTab === "character-image-assistants"
          ? (characterImageAssistantConfigs[0]?.assistant_code || "")
          : (["visuals", "frames", "characters", "voices", "music"].includes(params.get("section") || "") ? params.get("section") : "visuals");
    renderConfigPanels();
  } catch (error) {
    const list = $("providers_list");
    if (list) {
      list.innerHTML = `<div class="tasks-empty"><h3>加载失败</h3><p>${error.message}</p></div>`;
    }
    return;
  }

  $("providers_refresh")?.addEventListener("click", async () => {
    await loadProviderConfigsIntoState();
    renderConfigPanels();
  });
  $("story_assistants_refresh")?.addEventListener("click", async () => {
    await loadStoryAssistantConfigsIntoState();
    renderConfigPanels();
  });
  $("character_image_assistants_refresh")?.addEventListener("click", async () => {
    await loadCharacterImageAssistantConfigsIntoState();
    renderConfigPanels();
  });
  $("materials_refresh")?.addEventListener("click", async () => {
    materialConfigs = await fetchMaterialConfigs();
    renderConfigPanels();
  });

  document.addEventListener("change", (event) => {
    if (!pageIsProviders()) return;
    const input = event.target.closest("[data-material-file]");
    if (!input) return;
    const key = input.dataset.materialFile;
    setMaterialUploadState(key, input.files?.[0] || null);
    renderMaterialConfigPanel();
  });

  document.addEventListener("click", async (event) => {
    if (!pageIsProviders()) return;
    const configTabButton = event.target.closest("[data-config-tab]");
    const configSectionButton = event.target.closest("[data-config-section]");
    const providerCreateButton = event.target.closest("[data-provider-create]");
    const validateButton = event.target.closest("[data-provider-validate]");
    const saveButton = event.target.closest("[data-provider-save]");
    const storyAssistantCreateButton = event.target.closest("[data-story-assistant-create]");
    const storyAssistantValidateButton = event.target.closest("[data-story-assistant-validate]");
    const storyAssistantSaveButton = event.target.closest("[data-story-assistant-save]");
    const characterImageAssistantCreateButton = event.target.closest("[data-character-image-assistant-create]");
    const characterImageAssistantValidateButton = event.target.closest("[data-character-image-assistant-validate]");
    const characterImageAssistantSaveButton = event.target.closest("[data-character-image-assistant-save]");
    const materialCreateButton = event.target.closest("[data-material-create]");
    const materialSaveButton = event.target.closest("[data-material-save]");
    const materialDeleteButton = event.target.closest("[data-material-delete]");
    const materialClearButton = event.target.closest("[data-material-clear-file]");
    if (configTabButton) {
      activeConfigTab = configTabButton.dataset.configTab;
      activeConfigSection = activeConfigTab === "providers"
        ? (pendingCustomProviderDrafts[0]?.provider_code || providerConfigs[0]?.provider_code || "jimeng")
        : activeConfigTab === "assistants"
          ? (pendingStoryAssistantDrafts[0]?.id || storyAssistantConfigs[0]?.assistant_code || "")
          : activeConfigTab === "character-image-assistants"
            ? (pendingCharacterImageAssistantDrafts[0]?.id || characterImageAssistantConfigs[0]?.assistant_code || "")
          : "visuals";
      renderConfigPanels();
      return;
    }
    if (configSectionButton) {
      activeConfigSection = configSectionButton.dataset.configSection;
      renderConfigPanels();
      return;
    }
    if (materialClearButton) {
      clearMaterialUploadState(materialClearButton.dataset.materialClearFile);
      renderMaterialConfigPanel();
      return;
    }
    if (providerCreateButton) {
      const draft = providerDraft();
      pendingCustomProviderDrafts.unshift(draft);
      activeConfigTab = "providers";
      activeConfigSection = draft.provider_code;
      renderConfigPanels();
      return;
    }
    if (storyAssistantCreateButton) {
      const draft = storyAssistantDraft();
      pendingStoryAssistantDrafts.unshift(draft);
      activeConfigTab = "assistants";
      activeConfigSection = draft.id;
      renderConfigPanels();
      return;
    }
    if (characterImageAssistantCreateButton) {
      const draft = characterImageAssistantDraft();
      pendingCharacterImageAssistantDrafts.unshift(draft);
      activeConfigTab = "character-image-assistants";
      activeConfigSection = draft.id;
      renderConfigPanels();
      return;
    }
    if (!validateButton && !saveButton && !storyAssistantValidateButton && !storyAssistantSaveButton && !characterImageAssistantValidateButton && !characterImageAssistantSaveButton && !materialCreateButton && !materialSaveButton && !materialDeleteButton) return;

    const providerCode = validateButton?.dataset.providerValidate || saveButton?.dataset.providerSave;
    const payload = providerCode ? collectProviderForm(providerCode) : null;
    const errorNode = providerCode ? $(`provider_error_${providerCode}`) : null;
    let failureNode = errorNode;
    if (errorNode) errorNode.textContent = "";

    try {
      if (validateButton) {
        const result = await validateProviderConfig(providerCode, payload.provider_config_json);
        if (errorNode) errorNode.textContent = result.ok ? "配置校验通过。" : (result.errors || []).join("；");
      }
      if (saveButton) {
        await updateProviderConfig(providerCode, payload);
        const customDraftIndex = pendingCustomProviderDrafts.findIndex((item) => item.provider_code === providerCode);
        if (customDraftIndex >= 0) {
          pendingCustomProviderDrafts.splice(customDraftIndex, 1);
        }
        await loadProviderConfigsIntoState();
        renderConfigPanels();
      }
      if (storyAssistantValidateButton || storyAssistantSaveButton) {
        const [prefix, mode] = (storyAssistantValidateButton?.dataset.storyAssistantValidate || storyAssistantSaveButton?.dataset.storyAssistantSave).split(":");
        const payload = collectStoryAssistantForm(prefix);
        const assistantCode = (payload.assistant_code || "").trim();
        const storyAssistantErrorNode = $(`story_assistant_error_${prefix}`);
        failureNode = storyAssistantErrorNode;
        if (storyAssistantErrorNode) storyAssistantErrorNode.textContent = "";
        if (!assistantCode) throw new Error("助手标识不能为空");
        if (storyAssistantValidateButton) {
          const result = await validateStoryAssistantConfig(assistantCode, payload);
          if (storyAssistantErrorNode) storyAssistantErrorNode.textContent = result.ok ? "配置校验通过。" : (result.errors || []).join("；");
        }
        if (storyAssistantSaveButton) {
          await updateStoryAssistantConfig(assistantCode, payload);
          if (mode === "draft") {
            const index = pendingStoryAssistantDrafts.findIndex((item) => item.id === prefix);
            if (index >= 0) pendingStoryAssistantDrafts.splice(index, 1);
            activeConfigSection = assistantCode;
          }
          await loadStoryAssistantConfigsIntoState();
          renderConfigPanels();
        }
      }
      if (characterImageAssistantValidateButton || characterImageAssistantSaveButton) {
        const [prefix, mode] = (characterImageAssistantValidateButton?.dataset.characterImageAssistantValidate || characterImageAssistantSaveButton?.dataset.characterImageAssistantSave).split(":");
        const payload = collectCharacterImageAssistantForm(prefix);
        const assistantCode = (payload.assistant_code || "").trim();
        const characterImageErrorNode = $(`character_image_assistant_error_${prefix}`);
        failureNode = characterImageErrorNode;
        if (characterImageErrorNode) characterImageErrorNode.textContent = "";
        if (!assistantCode) throw new Error("助手标识不能为空");
        if (characterImageAssistantValidateButton) {
          const result = await validateCharacterImageAssistantConfig(assistantCode, payload);
          if (characterImageErrorNode) characterImageErrorNode.textContent = result.ok ? "配置校验通过。" : (result.errors || []).join("；");
        }
        if (characterImageAssistantSaveButton) {
          await updateCharacterImageAssistantConfig(assistantCode, payload);
          if (mode === "draft") {
            const index = pendingCharacterImageAssistantDrafts.findIndex((item) => item.id === prefix);
            if (index >= 0) pendingCharacterImageAssistantDrafts.splice(index, 1);
            activeConfigSection = assistantCode;
          }
          await loadCharacterImageAssistantConfigsIntoState();
          renderConfigPanels();
        }
      }
      if (materialCreateButton) {
        const type = materialCreateButton.dataset.materialCreate;
        pendingMaterialDrafts[type].unshift(materialDraft(type));
        renderMaterialConfigPanel();
      }
      if (materialSaveButton) {
        const [type, id, mode] = materialSaveButton.dataset.materialSave.split(":");
        const payload = collectMaterialForm(type, id);
        const file = collectMaterialFile(type, id);
        if (mode === "draft") {
          if (!file) throw new Error("新增素材必须上传文件");
          await createMaterialConfig(type, payload, file);
          pendingMaterialDrafts[type] = pendingMaterialDrafts[type].filter((item) => item.id !== id);
        } else {
          await updateMaterialConfig(type, id, payload, file);
        }
        materialConfigs = await fetchMaterialConfigs();
        clearMaterialUploadState(materialDraftKey(type, id));
        renderMaterialConfigPanel();
      }
      if (materialDeleteButton) {
        const [type, id, mode] = materialDeleteButton.dataset.materialDelete.split(":");
        clearMaterialUploadState(materialDraftKey(type, id));
        if (mode === "draft") {
          pendingMaterialDrafts[type] = pendingMaterialDrafts[type].filter((item) => item.id !== id);
        } else {
          await deleteMaterialConfig(type, id);
          materialConfigs = await fetchMaterialConfigs();
        }
        renderMaterialConfigPanel();
      }
    } catch (error) {
      if (failureNode) failureNode.textContent = error.message;
      if (materialSaveButton || materialDeleteButton) {
        const [type, id] = (materialSaveButton?.dataset.materialSave || materialDeleteButton?.dataset.materialDelete).split(":");
        const node = $(`material_error_${type}_${id}`);
        if (node) node.textContent = error.message;
      }
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
  initConfigCenter();
}
