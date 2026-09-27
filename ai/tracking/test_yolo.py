def main():
	from ultralytics import YOLO

	model = YOLO("yolov8n.pt")
	print("=" * 50)
	print("YOLO Loaded Successfully")
	print(model)
	print("=" * 50)


if __name__ == "__main__":
	main()