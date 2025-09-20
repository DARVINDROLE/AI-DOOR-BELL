from ultralytics import YOLO
import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse

app = FastAPI()

# Load pretrained YOLOv8 (COCO dataset has "person" class)
model = YOLO("yolov8n.pt")  # small model, fast for Raspberry Pi

@app.post("/detect")
async def detect_person(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return JSONResponse({"error": "Invalid image"}, status_code=400)

        results = model(img, verbose=False)

        found_person = False
        for r in results:
            for box in r.boxes:
                cls = int(box.cls[0])
                if model.names[cls] == "person":
                    found_person = True
                    break

        if found_person:
            return {"detected": True, "message": "hello world"}
        else:
            return {"detected": False}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
