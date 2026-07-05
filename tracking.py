import cv2
import mediapipe as mp
import math
import asyncio
import websockets
import json

mp_drawing = mp.solutions.drawing_utils
mp_holistic = mp.solutions.holistic

connected_clients = set()

# キャリブレーション（初期位置合わせ）用の変数
calibrated = False
calibration_frames = 0
pitch_offset_sum = 0.0
pitch_bias = 0.0  
mouth_offset_sum = 0.0
mouth_bias = 0.0  
eye_offset_sum = 0.0
eye_bias = 0.0  

async def tracking_server(websocket):
    connected_clients.add(websocket)
    print(f"ブラウザが接続しました。現在の接続数: {len(connected_clients)}")
    try:
        async for message in websocket:
            pass
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connected_clients.remove(websocket)
        print(f"ブラウザが切断されました。現在の接続数: {len(connected_clients)}")

async def main():
    global calibrated, calibration_frames, pitch_offset_sum, pitch_bias, mouth_offset_sum, mouth_bias, eye_offset_sum, eye_bias
    
    server = await websockets.serve(tracking_server, "localhost", 8765)
    print("WebSocketサーバーを localhost:8765 で起動しました。")

    cap = cv2.VideoCapture(0)

    with mp_holistic.Holistic(
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5) as holistic:

        while cap.isOpened():
            success, image = cap.read()
            if not success:
                break

            image.flags.writeable = False
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = holistic.process(image)
            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

            smile_degree = 0.0
            neck_pitch = 0.0 
            neck_yaw = 0.0   
            neck_roll = 0.0  
            mouth_open = 0.0 
            blink_value = 0.0 

            if results.face_landmarks:
                mp_drawing.draw_landmarks(
                    image, results.face_landmarks, mp_holistic.FACEMESH_TESSELATION,
                    mp_drawing.DrawingSpec(color=(80,110,10), thickness=1, circle_radius=1),
                    mp_drawing.DrawingSpec(color=(80,256,121), thickness=1, circle_radius=1)
                )

                right_eye_outer = results.face_landmarks.landmark[33]
                left_eye_outer = results.face_landmarks.landmark[263]
                nose_tip = results.face_landmarks.landmark[1]
                
                face_width = math.hypot(left_eye_outer.x - right_eye_outer.x, left_eye_outer.y - right_eye_outer.y)
                
                left_mouth = results.face_landmarks.landmark[61]
                right_mouth = results.face_landmarks.landmark[291]
                mouth_width = math.hypot(right_mouth.x - left_mouth.x, right_mouth.y - left_mouth.y)
                normalized_mouth = mouth_width / (face_width + 1e-6)

                left_eye_top = Antiquated = results.face_landmarks.landmark[159]
                left_eye_bottom = results.face_landmarks.landmark[145]
                left_eye_height = math.hypot(left_eye_top.x - left_eye_bottom.x, left_eye_top.y - left_eye_bottom.y)
                normalized_left_eye = left_eye_height / (face_width + 1e-6)

                right_eye_top = results.face_landmarks.landmark[386]
                right_eye_bottom = results.face_landmarks.landmark[374]
                right_eye_height = math.hypot(right_eye_top.x - right_eye_bottom.x, right_eye_top.y - right_eye_bottom.y)
                normalized_right_eye = right_eye_height / (face_width + 1e-6)

                avg_eye = (normalized_left_eye + normalized_right_eye) / 2.0

                v_lip_top = results.face_landmarks.landmark[13]
                v_lip_bottom = results.face_landmarks.landmark[14]
                mouth_height = math.hypot(v_lip_top.x - v_lip_bottom.x, v_lip_top.y - v_lip_bottom.y)
                normalized_mouth_height = mouth_height / (face_width + 1e-6)

                cv2.putText(image, f"Eye Ratio: {avg_eye:.3f}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
                cv2.putText(image, f"Mouth Ratio: {normalized_mouth:.3f}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

                # 【自動学習キャリブレーション】首・口・目を同時にサンプリング
                if not calibrated:
                    # 💡 【ここを修正！】エラーが出た代入を2行に綺麗に分けました
                    raw_pitch = (nose_tip.y - ((left_eye_outer.y + right_eye_outer.y) / 2)) / (face_width + 1e-6)
                    pitch_offset_sum += raw_pitch
                    
                    mouth_offset_sum += normalized_mouth_height
                    eye_offset_sum += avg_eye
                    calibration_frames += 1
                    cv2.putText(image, "Calibrating... Look Front Normal", (10, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                    if calibration_frames >= 10:
                        pitch_bias = pitch_offset_sum / 10.0
                        mouth_bias = mouth_offset_sum / 10.0
                        eye_bias = eye_offset_sum / 10.0
                        calibrated = True
                        print(f"学習完了！ 首:{pitch_bias:.2f}, 口:{mouth_bias:.2f}, 目:{eye_bias:.3f}")
                    neck_pitch = 0.0
                    mouth_open = 0.0
                    blink_value = 0.0
                    smile_degree = 0.0
                else:
                    # 1. 首の計算
                    center_y = (left_eye_outer.y + right_eye_outer.y) / 2
                    raw_pitch = (nose_tip.y - center_y) / (face_width + 1e-6)
                    neck_pitch = raw_pitch - pitch_bias

                    # 2. 口の計算（学習した初期値から開いた割合）
                    raw_open = (normalized_mouth_height - (mouth_bias + 0.03)) / 0.12
                    mouth_open = max(0.0, min(1.0, raw_open))

                    # 3. 瞬きの計算（学習した目の開き具合 eye_bias からの減少値で計算）
                    raw_blink = (eye_bias - avg_eye) / 0.045
                    blink_value = max(0.0, min(1.0, raw_blink))

                    # 4. 表清（笑顔）の計算
                    raw_smile = (normalized_mouth - 0.52) / 0.15
                    smile_degree = max(0.0, min(1.0, raw_smile))

                if normalized_mouth > 0.62 and avg_eye < 0.110:
                    smile_degree = max(smile_degree, 0.9)
                    cv2.putText(image, f"PERFECT SML: {smile_degree:.2f}", (10, 140), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 165, 255), 3)
                else:
                    cv2.putText(image, f"SMILE VAL: {smile_degree:.2f}", (10, 140), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (200, 200, 200), 3)
                
                dx = left_eye_outer.x - right_eye_outer.x
                dy = left_eye_outer.y - right_eye_outer.y
                neck_roll = math.atan2(dy, dx)

                center_x = (left_eye_outer.x + right_eye_outer.x) / 2
                neck_yaw = (nose_tip.x - center_x) / (face_width + 1e-6) * 1.5

            data = {
                "smile": smile_degree,
                "mouth_open": mouth_open, 
                "blink": blink_value, 
                "neck": {
                    "x": neck_pitch,
                    "y": neck_yaw,
                    "z": neck_roll
                }
            }

            if connected_clients:
                message = json.dumps(data)
                await asyncio.gather(*[client.send(message) for client in connected_clients])

            cv2.imshow('VTuber Tracking Server', image)
            if cv2.waitKey(5) & 0xFF == 27:
                break
            
            await asyncio.sleep(0.01)

    cap.release()
    cv2.destroyAllWindows()
    server.close()
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())