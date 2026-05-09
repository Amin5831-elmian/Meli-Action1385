import asyncio
import zipfile
import os
import re
import sys
import argparse
import shutil
from pyppeteer import launch
from urllib.parse import urlparse

def sanitize_filename(name: str) -> str:
    """Remove invalid characters for filenames."""
    return re.sub(r'[\\/*?:"<>|]', "_", name)

async def save_mhtml(url: str, output_file: str):
    """Save webpage as MHTML."""
    # اضافه کردن آرگومان‌های بیشتر برای پایداری
    browser = await launch(
        headless=True,
        args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu'
        ]
    )
    page = await browser.newPage()
    
    try:
        # تنظیم viewport برای اطمینان از رندر صحیح
        await page.setViewport({'width': 1920, 'height': 1080})
        
        # رفتن به صفحه با timeout بیشتر
        await page.goto(url, {
            'waitUntil': 'networkidle0',
            'timeout': 60000  # 60 ثانیه timeout
        })
        
        # روش صحیح دریافت MHTML
        client = await page.target.createCDPSession()
        mhtml_data = await client.send('Page.captureSnapshot', {'format': 'mhtml'})
        mhtml_content = mhtml_data['data']
        
        # ذخیره به صورت text (نه binary)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(mhtml_content)
            
    except Exception as e:
        print(f"❌ خطا در دریافت صفحه: {e}")
        raise
    finally:
        await browser.close()

def main():
    parser = argparse.ArgumentParser(description="Download a webpage as MHTML.")
    parser.add_argument("--url", required=True, help="URL of the page to download")
    parser.add_argument("--title", help="Optional title for the output file (without extension)")
    args = parser.parse_args()

    # Determine output filename
    if args.title:
        base_name = sanitize_filename(args.title)
    else:
        parsed = urlparse(args.url)
        path = parsed.path.strip('/').replace('/', '_')
        if path:
            base_name = sanitize_filename(path)
        else:
            base_name = sanitize_filename(parsed.netloc)
        if not base_name:
            base_name = "webpage"

    mhtml_filename = f"{base_name}.mhtml"
    zip_filename = f"{base_name}.zip"

    # Create download directory
    download_dir = "download"
    os.makedirs(download_dir, exist_ok=True)

    # Temporary folder for MHTML
    os.makedirs("temp", exist_ok=True)
    mhtml_path = os.path.join("temp", mhtml_filename)

    print(f"Downloading {args.url} → {mhtml_filename}")
    
    try:
        asyncio.run(save_mhtml(args.url, mhtml_path))
        
        # Create ZIP inside download folder
        zip_path = os.path.join(download_dir, zip_filename)
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(mhtml_path, arcname=mhtml_filename)
        
        print(f"✅ Created {zip_path} (contains {mhtml_filename})")
        
    except Exception as e:
        print(f"❌ خطا در اجرا: {e}")
        sys.exit(1)
    finally:
        # Cleanup temp
        shutil.rmtree("temp", ignore_errors=True)

if __name__ == "__main__":
    main()
