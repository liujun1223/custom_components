# Egreat Player for Home Assistant

通过 RS-232 串口控制亿格瑞播放器的 Home Assistant 自定义集成。

## 功能

- 开关机控制
- 播放/暂停/停止
- 音量加减
- 导航控制

## 安装

### 通过 HACS 安装

1. 添加自定义仓库：`https://github.com/liujun1223/custom_components.git`
2. 搜索并安装 "Egreat Player"
3. 重启 HA

### 手动安装

1. 下载 `custom_components/egreat_player` 文件夹
2. 复制到 HA 的 `custom_components` 目录
3. 重启 HA

## 配置

1. 设置 → 设备与服务 → 添加集成
2. 搜索 "Egreat Player"
3. 填写串口端口（如 `/dev/ttyUSB0`）和波特率（9600）

## 硬件要求

- 亿格瑞播放器（支持 RS-232 中控）
- USB 转 RS-232 串口线

## 反馈

[提交 Issue](https://github.com/liujun1223/custom_components/issues)