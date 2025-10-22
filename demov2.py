# -*- coding: utf-8 -*-
"""
基于 readme_assets/demov2 目录的素材，自动生成“我的剧名第13集”的剪映草稿。
实现内容：
- 读取视频片段（第13集-片段001~004.mp4），顺序拼接到视频轨道；
- 给片段之间添加转场；
- 读取字幕文本（无时间戳），按总时长等分到文本轨道；
- 可选：统一裁剪尾部若干秒；
- 草稿生成到剪映本地草稿目录下（不再多加 demo 子目录）。
限制说明：
- 字幕文件无时间戳，无法精准对齐发言，只能等分分配；若需精准字幕，请提供带时间码的 SRT/ASS。
- 自动导出成品依赖剪映窗口自动化（目前仅支持剪映6及以下），此脚本仅生成草稿，导出可后续手动或另开开关。
"""

import os
from datetime import datetime
from typing import List

import pyJianYingDraft as draft
from pyJianYingDraft import trange, tim, TransitionType

# ========== 配置 ==========
ROOT_DIR = r"C:\\Users\\lizhao1\\AppData\\Local\\JianyingPro\\User Data\\Projects\\com.lveditor.draft"
ASSETS_DIR = os.path.join(os.path.dirname(__file__), 'readme_assets', 'demov2')
EPISODE_NUM = 13
DRAFT_NAME = f"我的剧名第{EPISODE_NUM}集"
# 无时间戳字幕的等分策略：是否启用
ENABLE_EVEN_SUBTITLES = True
# 统一裁剪尾部秒数（0 表示不裁剪）
TAIL_TRIM_SECONDS = 0

# ========== 素材路径 ==========
FRAG_DIR = os.path.join(ASSETS_DIR, '视频片段', f'第{EPISODE_NUM}集')
SUBTITLE_PATH = os.path.join(ASSETS_DIR, '字幕', f'第0{EPISODE_NUM}集-字幕.txt')
OUTPUT_HINT_PATH = os.path.join(ROOT_DIR, DRAFT_NAME)


def list_fragments(dir_path: str) -> List[str]:
    files = [os.path.join(dir_path, f) for f in os.listdir(dir_path) if f.lower().endswith('.mp4')]
    files.sort()  # 依名称排序：片段001, 002, 003...
    if len(files) == 0:
        raise FileNotFoundError(f"未在 {dir_path} 找到 mp4 片段")
    return files


def read_subtitle_lines(path: str) -> List[str]:
    if not os.path.exists(path):
        print(f"字幕文件 {path} 不存在，跳过字幕生成")
        return []
    with open(path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
    return lines


def main() -> None:
    # 打印草稿目标目录提示（不创建 demo 子目录）
    draft_folder = draft.DraftFolder(ROOT_DIR)
    print(os.path.join(ROOT_DIR, DRAFT_NAME))

    # 创建草稿
    script = draft_folder.create_draft(DRAFT_NAME, 1920, 1080, allow_replace=True)

    # 添加轨道：视频 + 文本
    script.add_track(draft.TrackType.video).add_track(draft.TrackType.text)

    # 读取视频片段并顺序拼接
    frag_files = list_fragments(FRAG_DIR)
    video_segments = []
    last_end = tim("0s")
    for i, fp in enumerate(frag_files):
        material = draft.VideoMaterial(fp)
        seg = draft.VideoSegment(material, trange(last_end, material.duration))
        video_segments.append(seg)
        last_end = seg.end
    # 添加到脚本
    for seg in video_segments:
        script.add_segment(seg)
    # 添加转场（在前一段上添加）
    for i in range(1, len(video_segments)):
        video_segments[i - 1].add_transition(TransitionType.信号故障)

    # 字幕（无时间戳 -> 等分）
    if ENABLE_EVEN_SUBTITLES:
        lines = read_subtitle_lines(SUBTITLE_PATH)
        total_duration = last_end  # 微秒
        if len(lines) > 0 and total_duration > 0:
            # 计算每条字幕时长（尽量均分，至少 1 秒）
            per = max(total_duration // len(lines), tim("1s"))
            t = tim("0s")
            for text in lines:
                # 若剩余时长不足一条，最后一条顶到尾
                dur = per if t + per <= total_duration else (total_duration - t)
                if dur <= 0:
                    break
                txt = draft.TextSegment(
                    text,
                    trange(t, dur),
                    font=draft.FontType.文轩体,
                    style=draft.TextStyle(color=(1.0, 1.0, 0.0)),
                    clip_settings=draft.ClipSettings(transform_y=-0.8)
                )
                script.add_segment(txt)
                t = t + dur

    # 统一裁剪尾部
    if TAIL_TRIM_SECONDS and TAIL_TRIM_SECONDS > 0:
        trim_us = tim(f"{TAIL_TRIM_SECONDS}s")
        project_end = max(track.end_time for track in script.tracks.values() if len(track.segments) > 0)
        for track in script.tracks.values():
            if len(track.segments) == 0:
                continue
            last_seg = track.segments[-1]
            # 仅裁剪收尾到成品末尾的轨道，避免越界
            if last_seg.end == project_end:
                cut = min(trim_us, last_seg.duration)
                last_seg.duration = last_seg.duration - cut
        # 回写总时长
        script.duration = max(track.end_time for track in script.tracks.values())

    # 保存草稿
    script.save()

    print("草稿生成完成。请在剪映中打开草稿：", DRAFT_NAME)
    print("素材片段：", FRAG_DIR)
    print("字幕：", SUBTITLE_PATH)


if __name__ == '__main__':
    main()