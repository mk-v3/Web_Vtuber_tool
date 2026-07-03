import cv2
import mediapipe as mp
import math
import asyncio
import websockets
import json

mp_drawing = mp.solutions.drawing_utils
mp_holistic = mp.solutions.holistic

connected_clients = set()

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

            # 初期値
            smile_degree = 0.0
            neck_pitch = 0.0 # 上下
            neck_yaw = 0.0   # 左右
            neck_roll = 0.0  # かしげる

            if results.face_landmarks:
                mp_drawing.draw_landmarks(
                    image, results.face_landmarks, mp_holistic.FACEMESH_TESSELATION,
                    mp_drawing.DrawingSpec(color=(80,110,10), thickness=1, circle_radius=1),
                    mp_drawing.DrawingSpec(color=(80,256,121), thickness=1, circle_radius=1)
                )

                # --- 1. 顔の基本情報の取得 ---
                right_eye_outer = results.face_landmarks.landmark[33]
                left_eye_outer = results.face_landmarks.landmark[263]
                nose_tip = results.face_landmarks.landmark[1]
                
                face_width = math.hypot(left_eye_outer.x - right_eye_outer.x, left_eye_outer.y - right_eye_outer.y)
                
                # --- 2. 表情の正規化（元のデバッグ数値を活用） ---
                left_mouth = results.face_landmarks.landmark[61]
                right_mouth = results.face_landmarks.landmark[291]
                mouth_width = math.hypot(right_mouth.x - left_mouth.x, right_mouth.y - left_mouth.y)
                normalized_mouth = mouth_width / (face_width + 1e-6)

                left_eye_top = results.face_landmarks.landmark[159]
                left_eye_bottom = results.face_landmarks.landmark[145]
                left_eye_height = math.hypot(left_eye_top.x - left_eye_bottom.x, left_eye_top.y - left_eye_bottom.y)
                normalized_eye = left_eye_height / (face_width + 1e-6)

                # デバッグ表示
                cv2.putText(image, f"Eye Ratio: {normalized_eye:.3f}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
                cv2.putText(image, f"Mouth Ratio: {normalized_mouth:.3f}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

                # ▼ 変更点：0.0〜1.0の「滑らかな笑顔度」を計算
                # 0.45(真顔)〜0.65(満面の笑み)の間で割合を出し、0.0〜1.0の範囲に収める
                raw_smile = (normalized_mouth - 0.45) / 0.20
                smile_degree = max(0.0, min(1.0, raw_smile))

                # 完璧な笑顔の条件（元のコード）を満たしたら少し数値をブースト（補正）する
                if normalized_mouth > 0.60 and normalized_eye < 0.110:
                    smile_degree = max(smile_degree, 0.9) # 最低でも90%の笑顔にする
                    cv2.putText(image, f"PERFECT SML: {smile_degree:.2f}", (10, 140), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 165, 255), 3)
                else:
                    cv2.putText(image, f"SMILE VAL: {smile_degree:.2f}", (10, 140), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (200, 200, 200), 3)

                # --- 3. 首の角度計算（簡易推定モデル） ---
                # Roll（Z軸: 首をかしげる）
                dx = left_eye_outer.x - right_eye_outer.x
                dy = left_eye_outer.y - right_eye_outer.y
                neck_roll = math.atan2(dy, dx)

                # Yaw（Y軸: 左右を向く）
                center_x = (left_eye_outer.x + right_eye_outer.x) / 2
                # 鼻が顔の中心からどれくらいズレているかで計算（*1.5は動きの強調）
                neck_yaw = (nose_tip.x - center_x) / (face_width + 1e-6) * 1.5

                # Pitch（X軸: 上下を向く）
                center_y = (left_eye_outer.y + right_eye_outer.y) / 2
                # 基準位置(約0.3)からのズレで上下を計算（マイナスを掛けて反転を調整）
                neck_pitch = ((nose_tip.y - center_y) / (face_width + 1e-6) - 0.3) * -1.5

            # --- 送信データの構造をリッチに変更 ---
            data = {
                "smile": smile_degree,     # 0.0 ~ 1.0 の連続値に変更
                "neck": {
                    "x": neck_pitch,       # 上下
                    "y": neck_yaw,         # 左右
                    "z": neck_roll         # かしげる
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