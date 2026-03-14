# JSON → M3U Playlist Converter

Tự động chuyển đổi JSON playlist thành file M3U, chạy mỗi giờ trên GitHub Actions.

## 📋 Cấu trúc thư mục

```
.
├── .github/
│   └── workflows/
│       └── update-playlist.yml   ← GitHub Actions workflow
├── scripts/
│   └── convert.py                ← Script chuyển đổi
├── playlist.m3u                  ← File M3U đầu ra (tự động tạo)
└── README.md
```

## 🔧 Cách cài đặt

### Bước 1: Push code lên GitHub

```bash
git init
git add .
git commit -m "feat: add JSON to M3U playlist converter"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

### Bước 2: Thêm URL JSON vào GitHub Secrets

1. Vào repo GitHub → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Tên: `JSON_PLAYLIST_URL`
4. Giá trị: URL đầy đủ của file `channel.json`

### Bước 3: Kích hoạt Actions

1. Vào tab **Actions** trong repo
2. Nếu bị hỏi, click **"I understand my workflows, go ahead and enable them"**
3. Click workflow **"Update M3U Playlist"** → **"Run workflow"** để test thủ công

## 🔗 URL cố định của file M3U

Sau khi chạy thành công, file M3U có đường dẫn **raw cố định**:

```
https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/playlist.m3u
```

Thay `YOUR_USERNAME` và `YOUR_REPO` bằng thông tin thực của bạn.

## ⏰ Lịch chạy tự động

Workflow chạy **mỗi giờ một lần** (phút 00 mỗi giờ UTC).

> **Lưu ý:** GitHub có thể delay 5-15 phút so với lịch.

## 📦 Cấu trúc JSON được hỗ trợ

Script hỗ trợ nhiều dạng JSON phổ biến:

```json
// Dạng 1: List trực tiếp
[
  {
    "name": "Channel 1",
    "url": "https://stream.example.com/channel1.m3u8",
    "group": "News",
    "logo": "https://example.com/logo.png"
  }
]

// Dạng 2: Object với key 'channels'
{
  "channels": [...]
}

// Dạng 3: Object với key 'playlist', 'streams', 'data', 'items'
{
  "playlist": [...]
}
```

**Các field name được nhận diện tự động:**

| Field | Tên field chấp nhận |
|-------|---------------------|
| Tên kênh | `name`, `title`, `channel_name`, `channelName`, `label` |
| Stream URL | `url`, `stream_url`, `streamUrl`, `link`, `src`, `source` |
| Nhóm | `group`, `group_title`, `groupTitle`, `category`, `genre` |
| Logo | `logo`, `icon`, `tvg_logo`, `tvgLogo`, `image`, `thumbnail` |
| TVG ID | `tvg_id`, `tvgId`, `id`, `channel_id` |
