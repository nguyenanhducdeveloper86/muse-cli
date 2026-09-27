---
name: muse-multimedia
description: Generate high quality AI images, AI videos, and reference-based animations (image-to-video / image-to-image) via Muse.ai (Meta AI Personal Agent) using the `muse` CLI (`muse image`, `muse video`, `muse ask`).
metadata:
  version: 0.1.0
  author: Duc Nguyen
  provenance: local-custom
---

# Muse Multimedia & Agent Skill

Use this skill whenever you need to generate images, create videos, or animate reference pictures using the `muse` CLI powered by Muse.ai (Meta AI Personal Agent).

---

## 1. Commands Reference

### Text-to-Image Generation
```bash
muse image "<description>" [-o <output.png>]
```
- Example:
  ```bash
  muse image "Một chú mèo con phi hành gia trong không gian vũ trụ" -o cat.png
  ```

### Image-to-Image Generation (Reference Image)
```bash
muse image "<transformation description>" --ref <input_image.png> [-o <output.png>]
```
- Example:
  ```bash
  muse image "Biến ảnh này thành phong cách hoạt hình anime 3D" --ref my_avatar.png -o anime_avatar.png
  ```

### Text-to-Video Generation
```bash
muse video "<description>" [-o <output.mp4>]
```
- Example:
  ```bash
  muse video "Một chú robot nhỏ đang pha cà phê buổi sáng" -o robot_coffee.mp4
  ```

### Image-to-Video (Reference Image)
```bash
muse video "<motion description>" --ref <input_image.png> [-o <output.mp4>]
```
- Example:
  ```bash
  muse video "Nhân vật này đang mỉm cười và vẫy tay chào" --ref character.png -o anim.mp4
  ```

### Quick Q&A / Coding
```bash
muse ask "<question or coding task>"
```
