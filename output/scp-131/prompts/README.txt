=== scp-131 を Google AI Studio (aistudio.google.com) で手動生成する手順 ===

1. Nano Banana系の画像生成モデル（設定上は gemini-2.5-flash-image）のチャットを開く。
2. アスペクト比は 1:1 を選ぶ（AI StudioのUIに設定項目があれば）。
3. panel_N.txt の中身をそのままプロンプトとして貼り付け、末尾に[添付する...]の
   注記があれば同じ番号の panel_N_refs/ 内の画像を全て添付してから生成する。
4. 気に入った画像を output\scp-131\panels/panel_N.png として保存する（Nと採番を一致させること）。
5. このスタイルは前コマ参照が有効。panel_2以降はprompt末尾の注記に従い、直前1〜2コマの完成画像も参照画像として追加で添付すること。

全コマ分の画像を output\scp-131\panels/panel_N.png として保存し終えたら:
  python scripts/run_pipeline.py --id scp-131 --skip-generate
を実行すると、合成・15言語分のテキスト埋め込みまで自動で行われる。
