# makumi-fonts

Zen フォントシリーズ（Zen Antique, Zen Kaku Gothic Antique, Zen Kaku Gothic New, Zen Kurenaido, Zen Maru Gothic, Zen Old Mincho）の約物（句読点・括弧類など 28 文字）をサブセット化し、OpenType `chws`（約物詰め）機能を付加した Web フォントです。

![Makumi Antique Regular](specimens/makumi-antique-regular.png)

## 特徴

- **約物詰め（chws / vchw）対応**: 隣接する約物の余白を自動で詰める OpenType 機能を付加。
- **軽量サブセット**: 句読点・括弧類・約物 28 文字のみを収録（TTF, WOFF, WOFF2）。
- **フォント合成での利用**: CSS でベースフォントの手前に指定することで、約物のみカーニングを有効化。

## 利用方法

### CSS の読み込み (jsDelivr)

利用したいフォントファミリーに応じて、jsDelivr 経由で CSS を読み込みます。

```html
<link
  rel="stylesheet"
  href="https://cdn.jsdelivr.net/gh/daiji256/makumi-fonts@1.0.0/css/makumi-kaku-gothic-new.min.css"
/>
```

| フォントファミリー | 収録ウェイト | jsDelivr URL |
|---|---|---|
| すべて（全7書体） | 全ウェイト | `https://cdn.jsdelivr.net/gh/daiji256/makumi-fonts@1.0.0/css/makumi.min.css` |
| Makumi Antique | 400 | `https://cdn.jsdelivr.net/gh/daiji256/makumi-fonts@1.0.0/css/makumi-antique.min.css` |
| Makumi Antique Soft | 400 | `https://cdn.jsdelivr.net/gh/daiji256/makumi-fonts@1.0.0/css/makumi-antique-soft.min.css` |
| Makumi Kaku Gothic Antique | 300, 400, 500, 700, 900 | `https://cdn.jsdelivr.net/gh/daiji256/makumi-fonts@1.0.0/css/makumi-kaku-gothic-antique.min.css` |
| Makumi Kaku Gothic New | 300, 400, 500, 700, 900 | `https://cdn.jsdelivr.net/gh/daiji256/makumi-fonts@1.0.0/css/makumi-kaku-gothic-new.min.css` |
| Makumi Kurenaido | 400 | `https://cdn.jsdelivr.net/gh/daiji256/makumi-fonts@1.0.0/css/makumi-kurenaido.min.css` |
| Makumi Maru Gothic | 300, 400, 500, 700, 900 | `https://cdn.jsdelivr.net/gh/daiji256/makumi-fonts@1.0.0/css/makumi-maru-gothic.min.css` |
| Makumi Old Mincho | 400, 500, 600, 700, 900 | `https://cdn.jsdelivr.net/gh/daiji256/makumi-fonts@1.0.0/css/makumi-old-mincho.min.css` |

### CSS の設定

`font-family` の先頭に Makumi フォントを指定し、OpenType 機能 `chws` を有効にします。

```css
body {
  font-family: "Makumi Kaku Gothic New", "Zen Kaku Gothic New", sans-serif;
  font-feature-settings: "chws" 1;
}
```

## ビルドとテスト

[uv](https://github.com/astral-sh/uv) を使用してビルド、テスト、リント、フォーマットを実行します。

### ビルド

元フォントのダウンロード、chws 付加、サブセット化、TTF/WOFF/WOFF2 および CSS の書き出しを行います。

```bash
uv run build.py
```

### テスト

フォント整合性、CSS 配信ファイル、およびビジュアルリグレッションテストを実行します。

```bash
uv run test.py
```

ビジュアル specimen 画像を更新する場合は `--update` を指定します。

```bash
uv run test.py --update
```

### リント

Ruff による静的解析（コード検証）を実行します。

```bash
uvx ruff check
```

### フォーマット

Ruff によるコードフォーマットを適用します。

```bash
uvx ruff format
```

## ライセンス

- **フォント**: [SIL Open Font License 1.1](OFL.txt)
- **ビルド・テストスクリプト**: [MIT License](LICENSE)
