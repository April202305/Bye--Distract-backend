import cv2
from deepface import DeepFace
from collections import defaultdict, Counter

def analyze_video_emotions(input_video):
    cap = cv2.VideoCapture(input_video)

    # 获取视频参数（不打印）
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    frame_counter = 0
    results = defaultdict(list)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        current_second = frame_counter // fps

        # 每秒处理一次（选择每秒最后一帧）
        if frame_counter % fps == fps - 1:
            try:
                analysis = DeepFace.analyze(
                    img_path=frame,
                    actions=['emotion'],
                    detector_backend='retinaface',
                    enforce_detection=False
                )
                emotion_scores = analysis[0]['emotion']
                results[current_second].append(emotion_scores)
            except Exception as e:
                results[current_second].append({'error': str(e)})

        frame_counter += 1

    cap.release()

    # 全局统计（不打印）
    emotion_counter = Counter()
    for second in results.keys():
        valid_emotions = [
            max(res.items(), key=lambda x: x[1])[0]
            for res in results[second]
            if isinstance(res, dict) and 'error' not in res
        ]
        emotion_counter.update(valid_emotions)

    # 获取出现次数最多的两个情绪（仅名称）
    most_common_emotions = [emotion for emotion, _ in emotion_counter.most_common(2)]

    # 如果不足两个结果，补空字符串
    most_common_emotions += [''] * (2 - len(most_common_emotions))
    return most_common_emotions[:2]  # 确保返回两个值

# # 示例调用
# if __name__ == "__main__":
#     video_path = '1.mp4'
#     top_emotions = analyze_video_emotions(video_path)
#     print("\n==== 视频中的主要情绪 ====")
#     for emotion, count in top_emotions:
#         print(f"{emotion}: {count} 次")
