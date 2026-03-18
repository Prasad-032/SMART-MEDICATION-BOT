[app]
title = MedReminder
package.name = medreminder
package.domain = org.medreminder

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,ttf
source.include_patterns = MaterialIcons.ttf,NotoColorEmoji.ttf,users.json

version = 1.0

requirements = python3,kivy==2.3.0,plyer

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,VIBRATE,RECEIVE_BOOT_COMPLETED,POST_NOTIFICATIONS
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a

android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
