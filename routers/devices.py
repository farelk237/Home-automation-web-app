from fastapi import HTTPException

@app.post("/devices/{device_name}/toggle")
async def toggle_device(device_name: str):
    if device_name in devices:
        devices[device_name]["status"] = not devices[device_name]["status"]
        return {"message": f"{device_name} toggled", "status": devices[device_name]["status"]}
    else:
        raise HTTPException(status_code=404, detail="Device not found")
