import html


def body(config_text):
    return f"""
<h1>کپی کانفیگ</h1>
<p class="subtitle">متن را کپی کنید یا فایل را دانلود کنید.</p>
<section class="card">
<textarea id="cfg" readonly class="config-textarea">{html.escape(config_text)}</textarea>
<div class="actions actions-center">
  <button type="button" id="copy-btn">کپی متن کانفیگ</button>
  <a class="btn dark" href="/config">دانلود</a>
  <a class="btn dark" href="/">بازگشت</a>
</div>
<div id="copy-msg" class="copymsg" role="status"></div>
</section>
"""
