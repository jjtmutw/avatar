$ErrorActionPreference = "Stop"

$env:TORCH_HOME = "C:\tmp\torch_cache"
$env:MPLCONFIGDIR = "C:\tmp\matplotlib_cache"
$env:SADTALKER_FFMPEG = "C:\tmp\ffmpeg_bin\ffmpeg.exe"

$project = "C:\tmp\SadTalker_src\SadTalker-main"
$python = "C:\tmp\sadtalker_env\Scripts\python.exe"
$portrait = "C:\Users\jjpc2\Pictures\AI_design\ChatGPT Image 2026年5月28日 下午03_10_51 (2).png"
$audio = "C:\Users\jjpc2\Documents\虛擬助理\talking_avatar_output\xiaozheng_edge_neural_voice.wav"
$result = "C:\Users\jjpc2\Documents\虛擬助理\sadtalker_results"

New-Item -ItemType Directory -Force -Path $result | Out-Null
Set-Location $project

& $python inference.py `
  --driven_audio $audio `
  --source_image $portrait `
  --checkpoint_dir "$project\checkpoints" `
  --result_dir $result `
  --size 256 `
  --preprocess crop `
  --still `
  --cpu `
  --batch_size 1
