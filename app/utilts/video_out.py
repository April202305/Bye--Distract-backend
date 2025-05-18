import cv2
from deepface import DeepFace
from collections import defaultdict


def analyze_focus_emotions(video_path, focus_emotions, verbose=False):
    # 校验专注情绪合法性
    valid_emotions = ['angry', 'disgust', 'fear', 'happy', 'sad', 'surprise', 'neutral']
    invalid = set(focus_emotions) - set(valid_emotions)
    if invalid:
        raise ValueError(f"无效的专注情绪类型: {invalid}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError("无法打开视频文件")

    fps = int(cap.get(cv2.CAP_PROP_FPS))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if fps <= 0:
        fps = 1  # 防止除零
    total_seconds = total_frames // fps if total_frames > 0 else 0

    frame_counter = 0
    results = defaultdict(list)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # 每5秒分析一次（优化性能）
        if frame_counter % (fps * 5) == (fps * 5) - 1:
            current_second = frame_counter // fps
            try:
                analysis = DeepFace.analyze(
                    img_path=frame,
                    actions=['emotion'],
                    detector_backend='opencv',
                    enforce_detection=False
                )
                print(f"第 {current_second} 秒返回内容: {analysis}")
                emotion_dict = analysis[0]['emotion']
                results[current_second].append(emotion_dict)
            except Exception as e:
                if verbose:
                    print(f"第 {current_second} 秒分析失败: {str(e)}")

        frame_counter += 1

    cap.release()

    # 统计专注时间
    dominant_emotions = {}
    for sec, emo_list in results.items():
        for emo in emo_list:
            if isinstance(emo, dict):
                dominant = max(emo.items(), key=lambda x: x[1])[0]
                dominant_emotions[sec] = dominant
                break  # 每秒只取一个 dominant

    focus_seconds = [sec for sec, emo in dominant_emotions.items() if emo in focus_emotions]
    focus_ratio = len(focus_seconds)*5 / total_seconds if total_seconds > 0 else 0.0

    return focus_ratio

# # 示例调用
# result = analyze_focus_emotions("3.mp4", focus_emotions=["sad", "surprise"], verbose=True)
# print("专注时间占比：", result)
