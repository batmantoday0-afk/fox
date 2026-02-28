from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
import asyncio
from camoufox.async_api import AsyncCamoufox
import os

app = FastAPI()

@app.post("/solve")
async def solve_challenge(request: Request):
    try:
        data = await request.json()
        target_url = data.get("url")
        proxy = data.get("proxy")  # Expected format: http://user:pass@ip:port

        if not target_url:
            return JSONResponse({"status": "error", "message": "Missing 'url' parameter."}, status_code=400)

        # Launch stealth Camoufox browser
        camoufox_kwargs = {"headless": True}
        if proxy:
            camoufox_kwargs["proxy"] = {"server": proxy}

        print(f"[*] Solving CF for: {target_url} | Proxy: {proxy}")

        async with AsyncCamoufox(**camoufox_kwargs) as browser:
            page = await browser.new_page()
            
            # Go to the target URL
            await page.goto(target_url, wait_until="commit")
            
            # Wait a few seconds for Cloudflare to process the stealth fingerprint
            print("[*] Waiting for Cloudflare to process fingerprint...")
            await asyncio.sleep(5)
            
            # Check for cf_clearance specifically
            cf_clearance = None
            cookies = await page.context.cookies()
            for cookie in cookies:
                if cookie['name'] == 'cf_clearance':
                    cf_clearance = cookie
                    break
            
            html = await page.content()
            user_agent = await page.evaluate("navigator.userAgent")

            if cf_clearance:
                print("[+] Successfully generated cf_clearance!")
                return JSONResponse({
                    "status": "ok",
                    "message": "Challenge solved",
                    "solution": {
                        "url": page.url,
                        "response": html,
                        "cookies": cookies,
                        "userAgent": user_agent
                    }
                })
            else:
                 print("[-] Page loaded, but no cf_clearance cookie was generated.")
                 # It might mean CF didn't throw a challenge, or it's stuck. 
                 # We return OK with whatever cookies we have.
                 return JSONResponse({
                    "status": "ok",
                    "message": "Challenge not detected or cookie not generated.",
                    "solution": {
                        "url": page.url,
                        "response": html,
                        "cookies": cookies,
                        "userAgent": user_agent
                    }
                })

    except Exception as e:
        print(f"[!] Error: {str(e)}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.get("/")
def read_root():
    return {"status": "Camoufox API is running"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
