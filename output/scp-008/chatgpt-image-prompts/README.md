# scp-008 — ChatGPT Images 入力パケット

各 `panel_N.prompt.txt` はCodexが実際にChatGPT Imagesへ渡す完成プロンプトです。要約・言い換えをせず、ファイル全体をそのまま使用してください。

1. panel_1から順番にChatGPTの画像生成で、対応する `.prompt.txt` の全文を入力する。
2. `manifest.json` の `character_reference_files` があれば同時に添付する。panel_2以降は `previous_panel_references` の画像が存在すれば、それも添付して見た目を引き継ぐ。
3. 完成画像を `save_generated_image_as` に指定された名前で保存する。画像内に文字は入れない。
4. 全コマを保存した後、`after_generation` のコマンドで合成・各言語の文字埋め込みを行う。

`source.yaml` と `config/` は、プロンプトを確認・修正するための入力スナップショットです。
