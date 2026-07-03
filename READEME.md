# Web VTuber Tracking Tool

WebカメラとMediaPipeを使用した、ブラウザベースのリアルタイムVTuberトラッキングシステム。
Pythonで解析した顔情報をWebSocketでブラウザ（Three.js/VRM）に送り、3Dモデルを動かします。

## 🚀 Features
- **Real-time Tracking:** 笑顔、首の傾き、上半身の動きを低遅延でトラッキング。
- **Smooth Animation:** `lerp` による線形補間により、カメラノイズを抑えたぬるぬるした動きを実現。
- **High Compatibility:** VRM 0.0 / 1.0 双方に対応した自動ボーンマッピング。
- **Customizable:** OBS等の配信用に背景透過（グリーンバック）を標準サポート。

## 🛠 Tech Stack
- **Backend:** Python, MediaPipe, websockets
- **Frontend:** Three.js, @pixiv/three-vrm

## 💡 How to use
1. `pip install mediapipe opencv-python websockets` で環境を構築。
2. `tracking.py` を実行。
3. `index.html` をローカルサーバーで開く。

---
*Developed with the assistance of AI.*