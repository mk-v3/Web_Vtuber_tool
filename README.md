# AI-Assisted VRM Tracking Project

本プロジェクトは、AI（LLM）との対話を通じて構築された、MediaPipeとThree.jsを用いたリアルタイムVRMトラッキングシステムです。

## 🚀 開発コンセプト
- **AI-First Development**: コードの設計、デバッグ、仕様策定のすべてをAIとの対話によって進行。AIをメインの技術パートナーとして活用しています。
- **Auto-Calibration**: 起動時の1秒間でカメラ環境（照明や画角、個人の顔立ち）を自動解析し、瞬きや口パク、首の挙動を最適化するシステムを搭載。
- **Low-Latency Communication**: Pythonによる高速トラッキングデータ解析と、WebSocketを通じたブラウザベースのVRM描画によるリアルタイム性を実現。

## 🛠 現在の実装機能
1. **Holistic Tracking**: MediaPipe Holisticを使用した高精度な顔・首・上半身の認識。
2. **Auto-Calibration System**:
   - 起動直後の10フレームでベースラインを学習。
   - 瞬き（Blink）、口パク（Mouth Open）、首の向き（Pitch）の個体差を自動吸収。
3. **Optimized Expression Logic**:
   - 笑顔判定（Happy）と瞬きの連動制御（安全装置により、不自然な半眼を防止）。
   - 無表情時の数値遊び（Deadzone）設定による、口パクの誤作動抑制。
4. **Smooth Animation**: 
   - `THREE.MathUtils.lerp` を使用した各種補完処理により、カクつきのない滑らかな動きを実現。

## 📁 システム構成
- `tracking.py`: MediaPipeによる映像解析サーバー。WebSocketサーバーとしてデータを配信。
- `index.html`: Three.jsおよびThree-VRMを用いたレンダリング・クライアント。
- `sample.vrm`: 読み込み対象のアバターデータ。

## 💡 今後のロードマップ
1. **Eye Tracking**: 目線の自然な動き（瞳の追従）の実装。
2. **Body Movement**: 上半身のダイナミックな連動強化。
3. **Expression Triggers**: 感情表現のトリガー追加。
4. **Hand Tracking**: 大トリとしての手・指のトラッキング実装。