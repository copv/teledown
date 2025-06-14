import os
import re
import sys

from telethon import TelegramClient

from tools.tool import get_all_files, GetThumb, str2join, get_filetype
from tools.tqdm import TqdmUpTo


async def upload_file(client: TelegramClient, chat_id, path: str, del_after_upload: bool, addtag):
    from io import BytesIO
    from asyncio import CancelledError
    try:
        from moviepy.editor import VideoFileClip
    except ModuleNotFoundError:
        from moviepy.video.io.VideoFileClip import VideoFileClip
    from telethon.tl.types import DocumentAttributeVideo, PeerChannel
    isId = re.match(r'-?[1-9][0-9]{4,}', chat_id)
    isDir = os.path.isdir(path)
    if isId:
        chat_id = int(chat_id)
    if chat_id != 'me':
        if client.is_bot():
            peo = await client.get_entity(PeerChannel(chat_id))
        else:
            peo = await client.get_entity(chat_id)
    else:
        peo = 'me'
    path_list = []
    if isDir:
        path_list = get_all_files(path)
    else:
        path_list.append(path)
    # 遍历文件夹下的所有文件
    for file_path in path_list:
        # 如果文件不存在，跳过上传（防呆处理）
        if not os.path.exists(file_path):
            continue
        # 文件预处理，解析信息
        filename = os.path.basename(file_path)
        filename_without_ext = filename.rsplit('.', maxsplit=1)[0]
        file_size = os.path.getsize(file_path)
        # 发送文件到指定的群组或频道
        isVideo = get_filetype(file_path).startswith('video')
        if isVideo:
            try:
                thumb_input = await client.upload_file(BytesIO(GetThumb(file_path)))
                # 获取视频文件的时长
                video_duration = int(VideoFileClip(file_path).duration)
                # 获取视频文件的宽度和高度
                video_clip = VideoFileClip(file_path)
                video_width, video_height = video_clip.size
                video_clip.close()
                # 创建包含视频元数据的 DocumentAttributeVideo 对象
                video_attr = DocumentAttributeVideo(
                    duration=video_duration,  # 视频时长
                    w=video_width,  # 视频宽度
                    h=video_height,  # 视频高度
                    round_message=False,
                    supports_streaming=True
                )
            except OSError:
                thumb_input = video_attr = None
        else:
            thumb_input = video_attr = None
        with TqdmUpTo(total=file_size, desc=filename) as bar:
            # 上传文件到Telegram服务器
            try:
                result = await client.upload_file(file_path, progress_callback=bar.update_to)
            except CancelledError:
                print("取消上传")
                sys.exit()
            except Exception as e:
                print(f'上传出错，错误原因{e.__class__.__name__}，跳过{filename}')
                continue
            try:
                await client.send_file(
                    entity=peo,
                    file=result,
                    caption=filename_without_ext if addtag is None else str2join(f'#{addtag} ', filename_without_ext),
                    thumb=thumb_input,
                    progress_callback=bar.update_to,
                    attributes=[video_attr])
                if del_after_upload:
                    os.remove(file_path)
            except Exception:
                print(f'上传出错，疑似文件损坏，跳过{filename}')
    if isDir and not os.listdir(path):
        os.rmdir(path)
    # except Exception as e:
    #     print("上传出错", e.__class__.__name__)
