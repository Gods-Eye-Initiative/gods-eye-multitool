[app]

title = G.E.M.
package.name = gem
package.domain = org.gem
source.dir = .
source.include_exts = py,kv,atlas,txt,pem,crt
source.exclude_dirs = tests,.git,.venv,.venv-android,.buildozer,bin,__pycache__
version = 0.1.0
requirements = python3,kivy,cryptography
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,ACCESS_NETWORK_STATE
android.api = 35
android.minapi = 23
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
