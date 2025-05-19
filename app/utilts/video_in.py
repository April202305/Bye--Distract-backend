import cv2
from deepface import DeepFace
from collections import defaultdict, Counter

def analyze_video_emotions(input_video):
    cap = cv2.VideoCapture(input_video)

    # Get video parameters (no print)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    frame_counter = 0
    results = defaultdict(list)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        current_second = frame_counter // fps

        # Process once per second (select last frame of each second)
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

    # Global statistics (no print)
    emotion_counter = Counter()
    for second in results.keys():
        valid_emotions = [
            max(res.items(), key=lambda x: x[1])[0]
            for res in results[second]
            if isinstance(res, dict) and 'error' not in res
        ]
        emotion_counter.update(valid_emotions)

    # Get the top two emotions (only names)
    most_common_emotions = [emotion for emotion, _ in emotion_counter.most_common(2)]

    # If there are fewer than two results, add empty strings
    most_common_emotions += [''] * (2 - len(most_common_emotions))
    return most_common_emotions[:2]  # Ensure two values are returned

# # Example call
# if __name__ == "__main__":
#     video_path = '1.mp4'
#     top_emotions = analyze_video_emotions(video_path)
#     print("\n==== Video main emotions ====")
#     for emotion, count in top_emotions:
#         print(f"{emotion}: {count} times")
