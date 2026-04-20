"""
Training script for custom YOLOv8n waste detection model.

Usage:
    python -m backend.training.train --dataset <path_to_data.yaml> --epochs 100

This script fine-tunes YOLOv8n on a custom waste/garbage dataset.
You can obtain datasets from:
  - Roboflow Universe (search: "garbage bin overflow", "waste bin fill level")
  - TACO dataset (http://tacodataset.org/)
  - Custom collected & labeled images
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


def download_from_roboflow(api_key: str, workspace: str, project: str, version: int):
    """Download a dataset from Roboflow in YOLOv8 format."""
    try:
        from roboflow import Roboflow
    except ImportError:
        print("Install roboflow: pip install roboflow")
        sys.exit(1)

    rf = Roboflow(api_key=api_key)
    proj = rf.workspace(workspace).project(project)
    ds = proj.version(version)
    dataset = ds.download("yolov8")
    print(f"Dataset downloaded to: {dataset.location}")
    return dataset.location


def train(
    data_yaml: str,
    model: str = "yolov8n.pt",
    epochs: int = 100,
    imgsz: int = 640,
    batch: int = 16,
    name: str = "garbage_detector",
):
    """Fine-tune YOLOv8n on the given dataset."""
    from ultralytics import YOLO

    print(f"Loading base model: {model}")
    yolo = YOLO(model)

    print(f"Starting training on {data_yaml} for {epochs} epochs...")
    results = yolo.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        name=name,
        patience=20,
        save=True,
        plots=True,
        augment=True,
        # Augmentation settings
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        degrees=10.0,
        translate=0.1,
        scale=0.5,
        fliplr=0.5,
        mosaic=1.0,
        mixup=0.1,
    )

    best_weights = Path(f"runs/detect/{name}/weights/best.pt")
    print(f"\n✅ Training complete!")
    print(f"   Best weights: {best_weights}")
    print(f"   Results:      runs/detect/{name}/")
    print(f"\nTo use in the system, set MODEL_PATH={best_weights}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Train YOLOv8n for garbage detection")
    sub = parser.add_subparsers(dest="command")

    # Train command
    train_p = sub.add_parser("train", help="Train on a dataset")
    train_p.add_argument("--dataset", required=True, help="Path to data.yaml")
    train_p.add_argument("--model", default="yolov8n.pt", help="Base model")
    train_p.add_argument("--epochs", type=int, default=100)
    train_p.add_argument("--batch", type=int, default=16)
    train_p.add_argument("--imgsz", type=int, default=640)
    train_p.add_argument("--name", default="garbage_detector")

    # Download command
    dl_p = sub.add_parser("download", help="Download dataset from Roboflow")
    dl_p.add_argument("--api-key", required=True)
    dl_p.add_argument("--workspace", required=True)
    dl_p.add_argument("--project", required=True)
    dl_p.add_argument("--version", type=int, default=1)

    args = parser.parse_args()

    if args.command == "train":
        train(
            data_yaml=args.dataset,
            model=args.model,
            epochs=args.epochs,
            batch=args.batch,
            imgsz=args.imgsz,
            name=args.name,
        )
    elif args.command == "download":
        download_from_roboflow(
            api_key=args.api_key,
            workspace=args.workspace,
            project=args.project,
            version=args.version,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
