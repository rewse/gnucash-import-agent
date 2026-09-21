# GnuCash Import Skill Markdown再編設計

## 目的

`gnucash-import` skill配下のMarkdownを、共通手順とソース固有情報が重複しない構成へ再編する。個人を特定できる値は追跡対象のMarkdownとPythonから除き、gitignore対象の`references/personal.json`から読み込む。取引分類、重複検出、レビュー、SQL生成に必要な規則は維持する。

## 対象

- `.kiro/skills/gnucash-import/SKILL.md`
- `.kiro/skills/gnucash-import/references/**/*.md`
- `.kiro/skills/gnucash-import/references/templates/reference-template.md`
- `references/personal.json`を利用する関連スクリプト
- 個人固有の振込規則を持つ銀行スクリプト

`fixed-assets.md`にある帳簿方針やアカウントパスは取引分類の規則として残す。氏名、最寄り駅、家族関係に依存する振込パターン、個人間送金の固定額splitは個人設定へ移す。

## 文書構成

### SKILL.md

skillの起動条件と共通実行フローを保持する。

- statement取得からDB反映までの順序
- 一行単位の取込、曖昧な分類の確認、description、reconcile stateの規則
- 一意な作業ディレクトリと生成物の配置
- account GUID cacheの生成と更新
- 重複検出とクレジットカード明細の扱い
- 新規ソース追加手順
- account reference、schema、fixed assets、email lookup、personal settingsへの参照

Supported Sourcesの手書き一覧は削除し、`references/accounts/`と`scripts/`を正本として案内する。個別ソースの認証、画面操作、データ形式、マッピングはSKILL.mdへ載せない。

### Account references

全32ファイルを次の順序へ揃える。

1. `Accounts`: source accountとsource固有のtransfer account
2. `Access`: 認証、URL、画面遷移、取得方法、ページング
3. `Statement Data`: ブラウザまたはCSVの形式、ダミー例、入力形式、解析上の注意
4. `Mapping`: transaction pattern、account、description、split
5. `Source-specific Rules`: mirror transaction、skip、割引、多通貨、数量、履歴期間など

共通のcache確認、最終取引日の確認、review実行、SQL生成、DB実行、レビュー表のID・日付列、Email Lookup本文は削除する。必要な場合は共有文書への相対リンクだけを残す。`Script Template`見出しは削除し、対応スクリプトを冒頭の一行で示す。

### Shared references

- `email-lookup.md`: 固定されたMail DBバージョンと日付を変数化し、必要時だけ読む手順にする。
- `fixed-assets.md`: 重複を削るが、帳簿固有の資産計上、評価、売却規則を保持する。
- `gnucash-schema.md`: SQL生成に必要な最小スキーマ、valueとquantity、GUID、共通クエリを保持する。型表記とreconcile stateの説明をSKILL.mdと整合させる。
- `templates/reference-template.md`: account referenceの新構成に合わせ、共通ワークフローを再掲しない。

## Personal settings

実データはgitignore対象の`references/personal.json`へ保存する。追跡対象として`references/personal.example.json`を追加し、同じ構造にダミー値を置く。

```json
{
  "nearest_station": "Example Station",
  "transfer_rules": {
    "docomo_smtb_net_bank": {
      "family_deposit": {
        "account": "Income:Example",
        "amount": 12345,
        "description": "Family",
        "pattern": "振込＊EXAMPLE A"
      },
      "family_split": {
        "amount": -10000,
        "description": "Family",
        "pattern": "振込＊EXAMPLE B",
        "splits": [
          {
            "account": "Assets:Example",
            "amount": -6000
          },
          {
            "account": "Expenses:Example",
            "amount": -4000
          }
        ]
      },
      "friend_transfer": {
        "account": "Assets:Example",
        "pattern": "振込＊EXAMPLE C"
      },
      "self_transfer": {
        "account": "Assets:JPY - Current Assets:Banks:Example",
        "pattern": "振込＊EXAMPLE SELF"
      }
    },
    "mufg_bank": {
      "self_transfer": {
        "account": "Assets:JPY - Current Assets:Banks:Example",
        "contains": "EXAMPLE NAME"
      }
    },
    "sony_bank": {
      "self_transfer": {
        "account": "Assets:JPY - Current Assets:Banks:Example",
        "contains": "EXAMPLE NAME"
      }
    }
  }
}
```

各スクリプトは自分のsource keyだけを読む。account pathは`account-guid-cache.json`でGUIDへ変換する。必須の個人設定がない場合は起動時または該当取引の分類時に明確なエラーを出し、既定の口座へ推測分類しない。`nearest_station`はSuicaの通勤判定とPASMOの鉄道会社判定で利用する。

## Runtime path

一時スクリプトを`/tmp/gnucash-import.XXXXXX`から実行しても設定を解決できるようにする。リポジトリルートは環境変数`GNUCASH_IMPORT_ROOT`を優先し、未設定時は現在の作業ディレクトリから`.kiro/skills/gnucash-import`を確認する。通常はリポジトリルートから実行する。設定ファイルの絶対パスを一時スクリプトへ埋め込まない。

この解決方法は`account-guid-cache.json`と`personal.json`の両方に適用する。全スクリプトへの展開が必要なため、共通の小さなhelperを`script-template.py`へ依存させず、生成・コピーされる各スクリプトが自己完結する範囲で統一する。

## 整合性修正

- account referenceから`tmp/`固定パスを削除し、SKILL.mdの`$work_dir`へ統一する。
- `email-lookup.md`への相対リンクを修正する。
- `dpoint.md`のスクリプト名を`dpoint_import.py`へ修正する。
- browser commandを`agent-browser --auto-connect`へ統一する。
- 非NULLのtransaction descriptionだけを英語必須と明記する。
- 請求合計の一致は候補判定にとどめ、明細件数と内容を確認してから取込済みと判断する。
- schema例のreconcile stateを、statementで確認済みの取引は`c`、未確認の一般例は`n`と区別する。

## 検証

- 全Markdownの相対リンクが存在することをスクリプトで確認する。
- 32組のaccount referenceとimport scriptが一対一で対応することを確認する。
- 旧`tmp/`パス、壊れたスクリプト名、個人識別値、重複した定型文が残っていないことを検索する。
- `personal.example.json`と実`personal.json`の構文および必要キーを確認する。検証出力に実値は表示しない。
- 関連スクリプトについて、個人設定あり、設定なし、固定額split、未知の取引をテストする。
- 全Pythonファイルへ`compileall`と`basedpyright`を実行する。
- `git diff --check`と独立レビューで、ソース固有規則の欠落と意図しない個人情報の残存を確認する。

## 変更上の制約

取引分類の意味、splitの符号、通貨denominator、証券quantity、mirror transactionのskip条件は変更しない。文書の短縮時にダミー例を削りすぎず、解析に必要な列順、空欄、改行、全角文字は保持する。既存の未コミット変更と外部から加わったhook削除は保持する。
