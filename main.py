import os
import uuid
import zipfile
import subprocess
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# アップロードファイルと変換結果の保存先ディレクトリを作成
UPLOAD_FOLDER = "uploads"
CONVERTED_FOLDER = "converted"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)

# シンプルなアップロード用 HTML フォームを返すエンドポイント
@app.get("/", response_class=HTMLResponse)
async def read_root():
    return """
    <!doctype html>
    <html lang="ja">
      <head>
        <meta charset="utf-8">
        <title>DICOMからNIFTI変換アプリ（FastAPI版）</title>
      </head>
      <body>
        <h1>DICOMからNIFTI変換アプリ</h1>
        <form action="/upload" enctype="multipart/form-data" method="post">
          <p>
            DICOMデータが入ったZIPファイルを選択してください：<br>
            <input name="dicom_zip" type="file">
          </p>
          <p>
            <input type="submit" value="アップロード・変換">
          </p>
        </form>
      </body>
    </html>
    """

# アップロードされたファイルを受け取り変換を実行するエンドポイント
@app.post("/upload")
async def upload_dicom(dicom_zip: UploadFile = File(...)):
    # ZIPファイルかどうかを簡単にチェック
    if not dicom_zip.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="ZIPファイルをアップロードしてください。")
    
    # 一意のIDを生成し、アップロード先のフォルダを作成
    unique_id = str(uuid.uuid4())
    upload_path = os.path.join(UPLOAD_FOLDER, unique_id)
    os.makedirs(upload_path, exist_ok=True)
    
    zip_file_path = os.path.join(upload_path, dicom_zip.filename)
    with open(zip_file_path, "wb") as f:
        content = await dicom_zip.read()
        f.write(content)
    
    # ZIPファイルの解凍
    try:
        with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
            zip_ref.extractall(upload_path)
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="正しいZIPファイルではありません。")
    
    # 変換結果の出力フォルダを作成
    output_dir = os.path.join(CONVERTED_FOLDER, unique_id)
    os.makedirs(output_dir, exist_ok=True)
    
    # dcm2niix の実行（NIFTI ファイルは .nii.gz で出力）
    cmd = ["dcm2niix", "-z", "y", "-o", output_dir, upload_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print("stdout:", result.stdout)
    print("stderr:", result.stderr)
    
    # 出力された NIFTI ファイルを探す（拡張子 .nii.gz）
    try:
        files = os.listdir(output_dir)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="変換結果フォルダが見つかりません。")
    nifti_files = [f for f in files if f.endswith(".nii.gz")]
    
    if not nifti_files:
        raise HTTPException(status_code=500, detail="変換に失敗しました。")
    
    # 最初の NIFTI ファイルを返すためのダウンロード URL を作成
    download_url = f"/download/{unique_id}/{nifti_files[0]}"
    return {"message": "変換完了", "download_url": download_url}

# 変換されたファイルをダウンロードするエンドポイント
@app.get("/download/{unique_id}/{filename}")
async def download_file(unique_id: str, filename: str):
    file_path = os.path.join(CONVERTED_FOLDER, unique_id, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="ファイルが見つかりません。")
    return FileResponse(file_path, media_type="application/octet-stream", filename=filename)

# ※ Render 等で動作させる場合、環境変数 PORT を利用することも考えますが、
# uvicorn の起動時にホストとポートを指定してください。
