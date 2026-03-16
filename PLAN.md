# PetClip Studio — 项目计划（PM 每小时审查）

目标：把现有 `pet-anime-video` 改造成可售卖的 **PetClip Studio**。

## 交付验收（Definition of Done）
- Windows：生成 `PetClipStudio-Portable.exe`（免安装）
- 内置平台模板：抖音 + 小红书（各 ≥3 套）
- 导出素材包：
  - video.mp4
  - cover.png
  - title.txt
  - caption.txt
  - hashtags.txt
  - project.json（记录模板与参数，便于复用）
- UI：左上配置 / 左下素材 / 右侧输出（队列+预览+导出）
- 合规：不内置/不上传用户 API Key；不提交隐私素材；不引入明显高风险依赖；提供免责声明

## 里程碑与任务（M1→M4）
### M1 工作台 UI（Must）
- [x] UI 重构：PS式工作台布局（左上/左下/右侧）
- [x] 素材库：支持拖拽/上传（当前已实现：视频上传+列表；后续扩展图片/BGM/字幕/文案）
- [ ] 输出区：任务队列（单任务+历史也可）+ 预览播放器

### M2 平台模板体系（Must）
- [ ] 模板格式：platform template JSON（比例/时长/字幕安全区/封面尺寸）
- [ ] 抖音模板 x3：15s/25s/40s 9:16
- [ ] 小红书模板 x3：20s/35s/60s 9:16（封面更重）

### M3 导出素材包（Must）
- [ ] 成片 MP4 导出
- [ ] 封面 PNG 导出
- [ ] 文案/话题 TXT 导出
- [ ] project.json 导出（模板与参数）

### M4 Windows 打包与交付（Must）
- [ ] Windows Portable.exe 打包链路（脚本化）
- [ ] scripts/build_win.ps1（生成可发货 zip）
- [ ] scripts/build_linux.sh（为辅）
- [ ] README：是什么/怎么用/怎么打包/怎么发货

## 合规检查清单（每小时审查）
- [x] 仓库无明文密钥（扫描 sk- / api_key 等）
- [x] 未提交用户素材/输出到 git（.data/、uploads/、outputs/ 已忽略）
- [ ] 依赖无明显高危（npm/pip audit/requirements 变更可追踪）
- [ ] 默认本地生成路径可用，失败时提示清楚
