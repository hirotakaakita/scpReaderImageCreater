=== scp-027 をComfyUIで手動生成する手順 ===

このプロジェクトは通常 `python scripts/run_pipeline.py --id scp-027` でComfyUIのAPI (http://127.0.0.1:8188) を自動的に叩いて生成する（詳細: scripts/providers/comfyui/README.md）。
APIサーバーを使わずComfyUIのUIで手動生成したい場合:
1. ComfyUIのUIで scripts/providers/comfyui/workflow_api.json 相当のtxt2imgワークフロー（チェックポイント: None）を組む。
2. panel_N.txt の中身をPositive Promptノードに貼り付けて生成する。
3. 気に入った画像を output\scp-027\panels/panel_N.png として保存する（Nと採番を一致させること）。

全コマ分の画像を output\scp-027\panels/panel_N.png として保存し終えたら:
  python scripts/run_pipeline.py --id scp-027 --skip-generate
を実行すると、合成・15言語分のテキスト埋め込みまで自動で行われる。
