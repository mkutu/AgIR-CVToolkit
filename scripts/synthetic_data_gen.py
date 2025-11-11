import os
import random
from pathlib import Path
from typing import List, Tuple, Optional
import numpy as np
from PIL import Image
from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import partial


class SyntheticDataGenerator:
    """
    A tool to create synthetic training data by pasting plant segments around image edges
    and updating YOLO format detection files.
    """
    
    def __init__(self, 
                 images_dir: str,
                 labels_dir: Optional[str],
                 segments_dir: str,
                 output_images_dir: str,
                 output_labels_dir: str,
                 plant_class_id: int = 0,
                 random_n_sample: int = 10,
                 sample_w_replacement: bool = False):
        """
        Initialize the synthetic data generator.
        
        Args:
            images_dir: Directory containing source images
            labels_dir: Directory containing YOLO format .txt label files
            segments_dir: Directory containing RGBA plant cutout images
            output_images_dir: Directory to save augmented images
            output_labels_dir: Directory to save updated label files
            plant_class_id: YOLO class ID for the plant segments (default: 0)
        """
        self.images_dir = Path(images_dir)
        self.labels_dir = Path(labels_dir) if labels_dir else None
        self.segments_dir = Path(segments_dir)
        self.output_images_dir = Path(output_images_dir)
        self.output_labels_dir = Path(output_labels_dir)
        self.plant_class_id = plant_class_id
        self.random_n_sample = random_n_sample
        self.sample_w_replacement = sample_w_replacement
        
        # Create output directories
        self.output_images_dir.mkdir(parents=True, exist_ok=True)
        self.output_labels_dir.mkdir(parents=True, exist_ok=True)
        
        # Load all segment files
        self.segment_files = self._load_segment_files()
        print(f"Loaded {len(self.segment_files)} plant segments")
    
    def _load_segment_files(self) -> List[Path]:
        """Load all RGBA segment files from the segments directory."""
        segments = []
        for ext in ['*.png', '*.PNG']:
            segments.extend(self.segments_dir.glob(ext))
        return segments
    
    def _read_yolo_labels(self, label_path: Path) -> List[List[float]]:
        """
        Read YOLO format labels from a .txt file.
        
        Returns:
            List of labels, each as [class_id, x_center, y_center, width, height]
        """
        labels = []
        if label_path.exists():
            with open(label_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        values = list(map(float, line.split()))
                        labels.append(values)
        return labels
    
    def _write_yolo_labels(self, label_path: Path, labels: List[List[float]]):
        """Write YOLO format labels to a .txt file."""
        with open(label_path, 'w') as f:
            for label in labels:
                # Format: class_id x_center y_center width height
                line = f"{int(label[0])} {label[1]:.6f} {label[2]:.6f} {label[3]:.6f} {label[4]:.6f}\n"
                f.write(line)
    
    def _check_bbox_overlap(self, new_bbox: Tuple[int, int, int, int], 
                           existing_labels: List[List[float]], 
                           img_width: int, img_height: int,
                           overlap_threshold: float = 0.3) -> bool:
        """
        Check if a new bbox would significantly overlap with existing bboxes.
        
        Args:
            new_bbox: (x1, y1, x2, y2) in pixel coordinates
            existing_labels: List of existing labels in YOLO format
            img_width, img_height: Image dimensions
            overlap_threshold: Maximum allowed IoU (Intersection over Union) with existing boxes
            
        Returns:
            True if overlap is acceptable (below threshold), False if collision detected
        """
        if not existing_labels:
            return True
        
        new_x1, new_y1, new_x2, new_y2 = new_bbox
        new_area = (new_x2 - new_x1) * (new_y2 - new_y1)
        
        if new_area <= 0:
            return True
        
        for label in existing_labels:
            # Convert YOLO format to pixel coordinates
            _, x_center_norm, y_center_norm, width_norm, height_norm = label
            
            exist_width = width_norm * img_width
            exist_height = height_norm * img_height
            exist_x1 = (x_center_norm * img_width) - (exist_width / 2)
            exist_y1 = (y_center_norm * img_height) - (exist_height / 2)
            exist_x2 = exist_x1 + exist_width
            exist_y2 = exist_y1 + exist_height
            exist_area = exist_width * exist_height
            
            # Calculate intersection
            inter_x1 = max(new_x1, exist_x1)
            inter_y1 = max(new_y1, exist_y1)
            inter_x2 = min(new_x2, exist_x2)
            inter_y2 = min(new_y2, exist_y2)
            
            inter_width = max(0, inter_x2 - inter_x1)
            inter_height = max(0, inter_y2 - inter_y1)
            inter_area = inter_width * inter_height
            
            if inter_area > 0:
                # Calculate IoU (Intersection over Union)
                union_area = new_area + exist_area - inter_area
                iou = inter_area / union_area if union_area > 0 else 0
                
                # Also check if new bbox covers significant portion of existing bbox
                coverage = inter_area / exist_area if exist_area > 0 else 0
                
                # Reject if IoU is too high or if we're covering too much of existing bbox
                if iou > overlap_threshold or coverage > overlap_threshold:
                    return False
        
        return True
    
    def _get_edge_position(self, img_width: int, img_height: int, 
                          segment_width: int, segment_height: int,
                          edge: str, cutoff_percentage: float,
                          margin: int = 10) -> Tuple[int, int]:
        """
        Get a random position along a specified edge with controlled cutoff.
        
        Args:
            img_width: Width of the base image
            img_height: Height of the base image
            segment_width: Width of the segment to paste
            segment_height: Height of the segment to paste
            edge: Which edge to place on ('top', 'bottom', 'left', 'right')
            cutoff_percentage: Percentage of segment to cut off (0.0 to 1.0)
                              0.0 = fully inside, 1.0 = completely cut off
            margin: Minimum distance from corner (pixels)
            
        Returns:
            (x, y) position for top-left corner of segment
        """
        # Calculate offset based on cutoff percentage
        # The center of the segment will be placed at the edge of the frame
        # based on the cutoff percentage
        
        if edge == 'top':
            # Position along x-axis (random, with margins from corners)
            x = random.randint(margin, max(margin, img_width - segment_width - margin))
            # Position along y-axis (based on cutoff)
            # Center of segment at: 0 (edge) - (segment_height/2 * cutoff_percentage)
            center_y = -(segment_height / 2) * cutoff_percentage
            y = int(center_y - segment_height / 2)
            
        elif edge == 'bottom':
            x = random.randint(margin, max(margin, img_width - segment_width - margin))
            # Center at bottom edge, adjusted by cutoff
            center_y = img_height + (segment_height / 2) * cutoff_percentage
            y = int(center_y - segment_height / 2)
            
        elif edge == 'left':
            # Center at left edge, adjusted by cutoff
            center_x = -(segment_width / 2) * cutoff_percentage
            x = int(center_x - segment_width / 2)
            y = random.randint(margin, max(margin, img_height - segment_height - margin))
            
        else:  # right
            # Center at right edge, adjusted by cutoff
            center_x = img_width + (segment_width / 2) * cutoff_percentage
            x = int(center_x - segment_width / 2)
            y = random.randint(margin, max(margin, img_height - segment_height - margin))
        
        return (x, y)
    
    def _get_visible_plant_bbox(self, result_img: Image.Image, x: int, y: int, 
                                segment: Image.Image, img_width: int, img_height: int) -> Optional[Tuple[int, int, int, int]]:
        """
        Calculate tight bbox of actual visible plant pixels after pasting.
        
        This analyzes the segment in its final position and finds the tight bounds
        of only the visible, non-transparent pixels that fall within the frame.
        
        Args:
            result_img: The image after pasting (not used, but kept for context)
            x, y: Position where segment was pasted
            segment: The RGBA segment that was pasted
            img_width, img_height: Frame dimensions
            
        Returns:
            (x1, y1, x2, y2) in image coordinates, or None if nothing visible
        """
        # Get segment array
        seg_arr = np.array(segment)
        seg_height, seg_width = seg_arr.shape[:2]
        alpha = seg_arr[:, :, 3]
        
        # Find non-transparent pixels
        non_transparent = alpha > 10
        
        # Calculate the intersection with the frame
        # Segment occupies pixels from (x, y) to (x + seg_width, y + seg_height)
        # Frame is from (0, 0) to (img_width, img_height)
        
        # Clip segment bounds to frame
        seg_x1 = x
        seg_y1 = y
        seg_x2 = x + seg_width
        seg_y2 = y + seg_height
        
        frame_x1 = max(0, seg_x1)
        frame_y1 = max(0, seg_y1)
        frame_x2 = min(img_width, seg_x2)
        frame_y2 = min(img_height, seg_y2)
        
        # Check if any part is visible
        if frame_x1 >= frame_x2 or frame_y1 >= frame_y2:
            return None
        
        # Calculate which part of the segment is visible
        # If segment starts at x=-50, then visible part starts at segment_offset_x=50
        segment_offset_x = max(0, -seg_x1)
        segment_offset_y = max(0, -seg_y1)
        
        # Size of visible region in segment coordinates
        visible_width = frame_x2 - frame_x1
        visible_height = frame_y2 - frame_y1
        
        # Extract only the visible portion of the alpha channel
        visible_alpha = alpha[
            segment_offset_y:segment_offset_y + visible_height,
            segment_offset_x:segment_offset_x + visible_width
        ]
        
        # Find non-transparent pixels in visible region
        visible_non_transparent = visible_alpha > 10
        
        # Get tight bounds within visible region
        rows = np.any(visible_non_transparent, axis=1)
        cols = np.any(visible_non_transparent, axis=0)
        
        if not np.any(rows) or not np.any(cols):
            # No visible plant pixels
            return None
        
        row_indices = np.where(rows)[0]
        col_indices = np.where(cols)[0]
        
        # Tight bounds within visible region (relative to visible region)
        tight_y1 = int(row_indices[0])
        tight_y2 = int(row_indices[-1]) + 1
        tight_x1 = int(col_indices[0])
        tight_x2 = int(col_indices[-1]) + 1
        
        # Convert to image coordinates
        final_x1 = frame_x1 + tight_x1
        final_y1 = frame_y1 + tight_y1
        final_x2 = frame_x1 + tight_x2
        final_y2 = frame_y1 + tight_y2
        
        return (final_x1, final_y1, final_x2, final_y2)
    
    def _get_segment_bounds(self, segment: Image.Image) -> Tuple[int, int, int, int]:
        """
        Get the bounding box of non-transparent pixels in the segment.
        
        Args:
            segment: RGBA image
            
        Returns:
            (min_x, min_y, max_x, max_y) of non-transparent pixels
            Returns None if image is completely transparent
        """
        # Convert to numpy array for faster processing
        arr = np.array(segment)
        
        # Get alpha channel (transparency)
        alpha = arr[:, :, 3]
        
        # Find non-transparent pixels (alpha > threshold)
        non_transparent = alpha > 10  # Small threshold to handle anti-aliasing
        
        # Get coordinates of non-transparent pixels
        rows = np.any(non_transparent, axis=1)
        cols = np.any(non_transparent, axis=0)
        
        if not np.any(rows) or not np.any(cols):
            # Completely transparent
            return None
        
        row_indices = np.where(rows)[0]
        col_indices = np.where(cols)[0]
        
        min_y = int(row_indices[0])
        max_y = int(row_indices[-1]) + 1
        min_x = int(col_indices[0])
        max_x = int(col_indices[-1]) + 1
        
        return (min_x, min_y, max_x, max_y)
    
    def _bbox_to_yolo(self, x: int, y: int, width: int, height: int,
                     img_width: int, img_height: int) -> Tuple[float, float, float, float]:
        """
        Convert pixel bounding box to YOLO format.
        
        Args:
            x, y: Top-left corner of bounding box (can be negative or outside frame)
            width, height: Width and height of bounding box
            img_width, img_height: Dimensions of the image
            
        Returns:
            (x_center, y_center, width, height) normalized to [0, 1]
            Returns only the visible portion inside the frame
        """
        # Calculate the intersection of the bbox with the image frame
        # Original bbox bounds
        x1 = x
        y1 = y
        x2 = x + width
        y2 = y + height
        
        # Clip to image boundaries
        x1_clipped = max(0, x1)
        y1_clipped = max(0, y1)
        x2_clipped = min(img_width, x2)
        y2_clipped = min(img_height, y2)
        
        # Calculate actual visible width and height
        # Ensure non-negative (if bbox is completely outside, this will be 0)
        actual_width = max(0, x2_clipped - x1_clipped)
        actual_height = max(0, y2_clipped - y1_clipped)
        
        # Convert to YOLO format (normalized center coordinates and dimensions)
        # Handle edge case where bbox has zero dimensions
        if actual_width > 0 and actual_height > 0:
            x_center = (x1_clipped + actual_width / 2) / img_width
            y_center = (y1_clipped + actual_height / 2) / img_height
            norm_width = actual_width / img_width
            norm_height = actual_height / img_height
        else:
            # Return zero-size bbox (will be filtered out later)
            x_center = 0.0
            y_center = 0.0
            norm_width = 0.0
            norm_height = 0.0
        
        return (x_center, y_center, norm_width, norm_height)
    
    def process_image(self, image_path: Path, num_segments: int,
                     cutoff_range: Tuple[float, float] = (0.3, 0.7),
                     scale_range: Tuple[float, float] = (0.8, 1.2),
                     rotation_range: Tuple[int, int] = (-15, 15),
                     max_retries: int = 10,
                     overlap_threshold: float = 0.3) -> bool:
        """
        Process a single image by adding plant segments around the edges.
        
        Args:
            image_path: Path to the source image
            num_segments: Number of plant segments to add
            cutoff_range: Random range for how much is cut off by frame (min, max)
                         Each segment gets a random value in this range
                         0.0 = segment fully inside frame
                         0.5 = half of segment cut off (center at edge)
                         1.0 = segment fully outside frame
                         Example: (0.3, 0.7) gives variety from 30% to 70% cutoff
            scale_range: Random scale factor range for segments (min, max)
            rotation_range: Random rotation range in degrees (min, max)
            max_retries: Maximum attempts to find non-overlapping position per segment
            overlap_threshold: Maximum allowed IoU with existing bboxes (default: 0.3)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load base image
            base_img = Image.open(image_path).convert('RGBA')
            img_width, img_height = base_img.size
            
            # Load existing labels
            label_filename = image_path.stem + '.txt'
            if self.labels_dir and self.labels_dir.exists():
                label_path = self.labels_dir / label_filename
                existing_labels = self._read_yolo_labels(label_path)
            else:
                existing_labels = []

            # Create a copy for pasting
            result_img = base_img.copy()
            new_labels = existing_labels.copy()
            
            # Define edges to distribute segments
            edges = ['top', 'bottom', 'left', 'right']
            
            segments_added = 0
            segments_skipped = 0
            
            # Add segments
            for i in range(num_segments):
                # Randomly select a segment
                segment_path = random.choice(self.segment_files)
                segment = Image.open(segment_path).convert('RGBA')
                
                # Random transformations
                scale = random.uniform(*scale_range)
                rotation = random.randint(*rotation_range)
                cutoff_percentage = random.uniform(*cutoff_range)  # Random cutoff for this segment
                
                # Scale segment
                new_width = int(segment.width * scale)
                new_height = int(segment.height * scale)
                segment = segment.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Rotate segment
                segment = segment.rotate(rotation, expand=True, resample=Image.Resampling.BICUBIC)
                seg_width, seg_height = segment.size
                
                # Select edge (cycle through edges for even distribution)
                edge = edges[i % len(edges)]
                
                # Try to find a non-overlapping position
                placement_found = False
                for attempt in range(max_retries):
                    # Get position on edge (using full segment dimensions for positioning)
                    x, y = self._get_edge_position(img_width, img_height, 
                                                  seg_width, seg_height, edge,
                                                  cutoff_percentage)
                    
                    # Calculate what the visible bbox would be at this position
                    temp_bbox = self._get_visible_plant_bbox(result_img, x, y, segment, 
                                                            img_width, img_height)
                    
                    if temp_bbox is None:
                        # No visible pixels, try another position
                        continue
                    
                    # Check for collision with existing labels
                    if self._check_bbox_overlap(temp_bbox, new_labels, img_width, img_height, 
                                               overlap_threshold):
                        # Good position found, paste the segment
                        result_img.paste(segment, (x, y), segment)
                        visible_bbox = temp_bbox
                        placement_found = True
                        break
                
                if not placement_found:
                    # Could not find non-overlapping position after max retries
                    segments_skipped += 1
                    continue
                
                bbox_x1, bbox_y1, bbox_x2, bbox_y2 = visible_bbox
                bbox_width = bbox_x2 - bbox_x1
                bbox_height = bbox_y2 - bbox_y1
                
                # Convert to YOLO format
                x_center = (bbox_x1 + bbox_width / 2) / img_width
                y_center = (bbox_y1 + bbox_height / 2) / img_height
                norm_width = bbox_width / img_width
                norm_height = bbox_height / img_height
                
                # Add to labels (bbox is already validated as non-zero)
                new_label = [self.plant_class_id, x_center, y_center, norm_width, norm_height]
                new_labels.append(new_label)
                segments_added += 1
            
            # Save augmented image
            output_image_path = self.output_images_dir / image_path.name
            result_img.convert('RGB').save(output_image_path)
            
            # Save updated labels
            output_label_path = self.output_labels_dir / label_filename
            self._write_yolo_labels(output_label_path, new_labels)
            
            if segments_skipped > 0:
                print(f"✓ Processed {image_path.name} - added {segments_added}/{num_segments} segments ({segments_skipped} skipped due to overlap)")
            else:
                print(f"✓ Processed {image_path.name} - added {segments_added} segments")
            return True
            
        except Exception as e:
            print(f"✗ Error processing {image_path.name}: {str(e)}")
            return False
    
    def process_dataset(self, num_segment_range: int,
                       cutoff_range: Tuple[float, float] = (0.3, 0.7),
                       scale_range: Tuple[float, float] = (0.8, 1.2),
                       rotation_range: Tuple[int, int] = (-15, 15),
                       n_workers: Optional[int] = None,
                       max_retries: int = 10,
                       overlap_threshold: float = 0.3):
        """
        Process all images in the dataset using multiprocessing.
        
        Args:
            num_segments: Number of plant segments to add to each image
            cutoff_range: Random range for cutoff (min, max) - each segment picks randomly
            scale_range: Random scale factor range for segments
            rotation_range: Random rotation range in degrees
            n_workers: Number of worker processes (None = auto-detect, 1 = no multiprocessing)
            max_retries: Maximum attempts to find non-overlapping position per segment
            overlap_threshold: Maximum allowed IoU with existing bboxes (default: 0.3)
        """
        # Find all images
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']
        image_files = []
        for ext in image_extensions:
            image_files.extend(self.images_dir.glob(ext))
        
        if self.random_n_sample:
            if self.random_n_sample > len(image_files) and self.sample_w_replacement:
                image_files = random.choices(image_files, k=self.random_n_sample)
            else:
                image_files = random.sample(image_files, min(self.random_n_sample, len(image_files)))
        
        print(f"\nProcessing {len(image_files)} images...")
        print(f"Adding {num_segment_range} segments per image")
        print(f"Collision detection: overlap_threshold={overlap_threshold}, max_retries={max_retries}")
        
        # Determine number of workers
        if n_workers is None:
            n_workers = max(1, os.cpu_count() - 1)  # Leave one CPU free
        num_segments = random.randint(num_segment_range[0], num_segment_range[1])
        if n_workers == 1 or len(image_files) == 1:
            # Single-threaded processing
            print(f"Using single-threaded processing\n")
            successful = 0
            for img_path in image_files:
                if self.process_image(img_path, num_segments, cutoff_range, 
                                    scale_range, rotation_range, max_retries, overlap_threshold):
                    successful += 1
        else:
            # Multi-threaded processing
            print(f"Using {n_workers} worker processes\n")
            
            # Create a partial function with fixed parameters
            process_func = partial(
                _process_image_worker,
                labels_dir=self.labels_dir,
                segments_dir=self.segments_dir,
                segment_files=self.segment_files,
                output_images_dir=self.output_images_dir,
                output_labels_dir=self.output_labels_dir,
                plant_class_id=self.plant_class_id,
                num_segments=num_segments,
                cutoff_range=cutoff_range,
                scale_range=scale_range,
                rotation_range=rotation_range,
                max_retries=max_retries,
                overlap_threshold=overlap_threshold
            )
            
            # Process images in parallel
            successful = 0
            with ProcessPoolExecutor(max_workers=n_workers) as executor:
                # Submit all tasks
                future_to_image = {executor.submit(process_func, img_path): img_path 
                                  for img_path in image_files}
                
                # Process completed tasks as they finish
                for future in as_completed(future_to_image):
                    if future.result():
                        successful += 1
        
        print(f"\n{'='*50}")
        print(f"Processing complete!")
        print(f"Successfully processed: {successful}/{len(image_files)} images")
        print(f"Output images: {self.output_images_dir}")
        print(f"Output labels: {self.output_labels_dir}")
        print(f"{'='*50}")


def _get_visible_plant_bbox_worker(result_img: Image.Image, x: int, y: int, 
                                   segment: Image.Image, img_width: int, img_height: int) -> Optional[Tuple[int, int, int, int]]:
    """
    Calculate tight bbox of actual visible plant pixels after pasting (worker version).
    """
    # Get segment array
    seg_arr = np.array(segment)
    seg_height, seg_width = seg_arr.shape[:2]
    alpha = seg_arr[:, :, 3]
    
    # Calculate the intersection with the frame
    seg_x1 = x
    seg_y1 = y
    seg_x2 = x + seg_width
    seg_y2 = y + seg_height
    
    frame_x1 = max(0, seg_x1)
    frame_y1 = max(0, seg_y1)
    frame_x2 = min(img_width, seg_x2)
    frame_y2 = min(img_height, seg_y2)
    
    # Check if any part is visible
    if frame_x1 >= frame_x2 or frame_y1 >= frame_y2:
        return None
    
    # Calculate which part of the segment is visible
    segment_offset_x = max(0, -seg_x1)
    segment_offset_y = max(0, -seg_y1)
    
    # Size of visible region
    visible_width = frame_x2 - frame_x1
    visible_height = frame_y2 - frame_y1
    
    # Extract only the visible portion of the alpha channel
    visible_alpha = alpha[
        segment_offset_y:segment_offset_y + visible_height,
        segment_offset_x:segment_offset_x + visible_width
    ]
    
    # Find non-transparent pixels in visible region
    visible_non_transparent = visible_alpha > 10
    
    # Get tight bounds within visible region
    rows = np.any(visible_non_transparent, axis=1)
    cols = np.any(visible_non_transparent, axis=0)
    
    if not np.any(rows) or not np.any(cols):
        return None
    
    row_indices = np.where(rows)[0]
    col_indices = np.where(cols)[0]
    
    # Tight bounds within visible region
    tight_y1 = int(row_indices[0])
    tight_y2 = int(row_indices[-1]) + 1
    tight_x1 = int(col_indices[0])
    tight_x2 = int(col_indices[-1]) + 1
    
    # Convert to image coordinates
    final_x1 = frame_x1 + tight_x1
    final_y1 = frame_y1 + tight_y1
    final_x2 = frame_x1 + tight_x2
    final_y2 = frame_y1 + tight_y2
    
    return (final_x1, final_y1, final_x2, final_y2)


def _get_segment_bounds_worker(segment: Image.Image) -> Tuple[int, int, int, int]:
    """
    Get the bounding box of non-transparent pixels in the segment.
    
    Args:
        segment: RGBA image
        
    Returns:
        (min_x, min_y, max_x, max_y) of non-transparent pixels
        Returns None if image is completely transparent
    """
    # Convert to numpy array for faster processing
    arr = np.array(segment)
    
    # Get alpha channel (transparency)
    alpha = arr[:, :, 3]
    
    # Find non-transparent pixels (alpha > threshold)
    non_transparent = alpha > 10  # Small threshold to handle anti-aliasing
    
    # Get coordinates of non-transparent pixels
    rows = np.any(non_transparent, axis=1)
    cols = np.any(non_transparent, axis=0)
    
    if not np.any(rows) or not np.any(cols):
        # Completely transparent
        return None
    
    row_indices = np.where(rows)[0]
    col_indices = np.where(cols)[0]
    
    min_y = int(row_indices[0])
    max_y = int(row_indices[-1]) + 1
    min_x = int(col_indices[0])
    max_x = int(col_indices[-1]) + 1
    
    return (min_x, min_y, max_x, max_y)


def _check_bbox_overlap_worker(new_bbox: Tuple[int, int, int, int], 
                               existing_labels: List[List[float]], 
                               img_width: int, img_height: int,
                               overlap_threshold: float = 0.3) -> bool:
    """
    Check if a new bbox would significantly overlap with existing bboxes.
    Worker version for multiprocessing.
    
    Args:
        new_bbox: (x1, y1, x2, y2) in pixel coordinates
        existing_labels: List of existing labels in YOLO format
        img_width, img_height: Image dimensions
        overlap_threshold: Maximum allowed IoU (Intersection over Union) with existing boxes
        
    Returns:
        True if overlap is acceptable (below threshold), False if collision detected
    """
    if not existing_labels:
        return True
    
    new_x1, new_y1, new_x2, new_y2 = new_bbox
    new_area = (new_x2 - new_x1) * (new_y2 - new_y1)
    
    if new_area <= 0:
        return True
    
    for label in existing_labels:
        # Convert YOLO format to pixel coordinates
        _, x_center_norm, y_center_norm, width_norm, height_norm = label
        
        exist_width = width_norm * img_width
        exist_height = height_norm * img_height
        exist_x1 = (x_center_norm * img_width) - (exist_width / 2)
        exist_y1 = (y_center_norm * img_height) - (exist_height / 2)
        exist_x2 = exist_x1 + exist_width
        exist_y2 = exist_y1 + exist_height
        exist_area = exist_width * exist_height
        
        # Calculate intersection
        inter_x1 = max(new_x1, exist_x1)
        inter_y1 = max(new_y1, exist_y1)
        inter_x2 = min(new_x2, exist_x2)
        inter_y2 = min(new_y2, exist_y2)
        
        inter_width = max(0, inter_x2 - inter_x1)
        inter_height = max(0, inter_y2 - inter_y1)
        inter_area = inter_width * inter_height
        
        if inter_area > 0:
            # Calculate IoU (Intersection over Union)
            union_area = new_area + exist_area - inter_area
            iou = inter_area / union_area if union_area > 0 else 0
            
            # Also check if new bbox covers significant portion of existing bbox
            coverage = inter_area / exist_area if exist_area > 0 else 0
            
            # Reject if IoU is too high or if we're covering too much of existing bbox
            if iou > overlap_threshold or coverage > overlap_threshold:
                return False
    
    return True


def _process_image_worker(image_path: Path,
                         labels_dir: Path,
                         segments_dir: Path,
                         segment_files: List[Path],
                         output_images_dir: Path,
                         output_labels_dir: Path,
                         plant_class_id: int,
                         num_segments: int,
                         cutoff_range: Tuple[float, float],
                         scale_range: Tuple[float, float],
                         rotation_range: Tuple[int, int],
                         max_retries: int = 10,
                         overlap_threshold: float = 0.3) -> bool:
    """
    Worker function for multiprocessing. Must be at module level to be picklable.
    
    This function replicates the logic from process_image but as a standalone function.
    """
    try:
        # Load base image
        base_img = Image.open(image_path).convert('RGBA')
        img_width, img_height = base_img.size
        
        existing_labels = []
        # Load existing labels
        label_filename = image_path.stem + '.txt'
        if labels_dir:
            label_path = labels_dir / label_filename
            # Read existing labels
            if label_path.exists():
                with open(label_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            values = list(map(float, line.split()))
                            existing_labels.append(values)
        
        # Create a copy for pasting
        result_img = base_img.copy()
        new_labels = existing_labels.copy()
        
        # Define edges to distribute segments
        edges = ['top', 'bottom', 'left', 'right']
        
        segments_added = 0
        segments_skipped = 0
        
        # Add segments
        for i in range(num_segments):
            # Randomly select a segment
            segment_path = random.choice(segment_files)
            segment = Image.open(segment_path).convert('RGBA')
            
            # Random transformations
            scale = random.uniform(*scale_range)
            rotation = random.randint(*rotation_range)
            cutoff_percentage = random.uniform(*cutoff_range)
            
            # Scale segment
            new_width = int(segment.width * scale)
            new_height = int(segment.height * scale)
            segment = segment.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Rotate segment
            segment = segment.rotate(rotation, expand=True, resample=Image.Resampling.BICUBIC)
            seg_width, seg_height = segment.size
            
            # Select edge (cycle through edges for even distribution)
            edge = edges[i % len(edges)]
            
            # Try to find a non-overlapping position
            placement_found = False
            for attempt in range(max_retries):
                # Get position on edge (using full segment dimensions for positioning)
                x, y = _get_edge_position_worker(img_width, img_height, 
                                                seg_width, seg_height, edge,
                                                cutoff_percentage)
                
                # Calculate what the visible bbox would be at this position
                temp_bbox = _get_visible_plant_bbox_worker(result_img, x, y, segment, 
                                                          img_width, img_height)
                
                if temp_bbox is None:
                    # No visible pixels, try another position
                    continue
                
                # Check for collision with existing labels
                if _check_bbox_overlap_worker(temp_bbox, new_labels, img_width, img_height, 
                                             overlap_threshold):
                    # Good position found, paste the segment
                    result_img.paste(segment, (x, y), segment)
                    visible_bbox = temp_bbox
                    placement_found = True
                    break
            
            if not placement_found:
                # Could not find non-overlapping position after max retries
                segments_skipped += 1
                continue
            
            bbox_x1, bbox_y1, bbox_x2, bbox_y2 = visible_bbox
            bbox_width = bbox_x2 - bbox_x1
            bbox_height = bbox_y2 - bbox_y1
            
            # Convert to YOLO format
            x_center = (bbox_x1 + bbox_width / 2) / img_width
            y_center = (bbox_y1 + bbox_height / 2) / img_height
            norm_width = bbox_width / img_width
            norm_height = bbox_height / img_height
            
            # Add to labels (bbox is already validated as non-zero)
            new_label = [plant_class_id, x_center, y_center, norm_width, norm_height]
            new_labels.append(new_label)
            segments_added += 1
        
        # Save augmented image
        output_image_path = output_images_dir / image_path.name
        result_img.convert('RGB').save(output_image_path)
        
        # Save updated labels
        output_label_path = output_labels_dir / label_filename
        with open(output_label_path, 'w') as f:
            for label in new_labels:
                line = f"{int(label[0])} {label[1]:.6f} {label[2]:.6f} {label[3]:.6f} {label[4]:.6f}\n"
                f.write(line)
        
        if segments_skipped > 0:
            print(f"✓ Processed {image_path.name} - added {segments_added}/{num_segments} segments ({segments_skipped} skipped due to overlap)")
        else:
            print(f"✓ Processed {image_path.name} - added {segments_added} segments")
        return True
        
    except Exception as e:
        print(f"✗ Error processing {image_path.name}: {str(e)}")
        return False


def _get_edge_position_worker(img_width: int, img_height: int, 
                              segment_width: int, segment_height: int,
                              edge: str, cutoff_percentage: float,
                              margin: int = 10) -> Tuple[int, int]:
    """Helper function for getting edge position in worker process."""
    if edge == 'top':
        x = random.randint(margin, max(margin, img_width - segment_width - margin))
        center_y = -(segment_height / 2) * cutoff_percentage
        y = int(center_y - segment_height / 2)
    elif edge == 'bottom':
        x = random.randint(margin, max(margin, img_width - segment_width - margin))
        center_y = img_height + (segment_height / 2) * cutoff_percentage
        y = int(center_y - segment_height / 2)
    elif edge == 'left':
        center_x = -(segment_width / 2) * cutoff_percentage
        x = int(center_x - segment_width / 2)
        y = random.randint(margin, max(margin, img_height - segment_height - margin))
    else:  # right
        center_x = img_width + (segment_width / 2) * cutoff_percentage
        x = int(center_x - segment_width / 2)
        y = random.randint(margin, max(margin, img_height - segment_height - margin))
    
    return (x, y)


def _bbox_to_yolo_worker(x: int, y: int, width: int, height: int,
                        img_width: int, img_height: int) -> Tuple[float, float, float, float]:
    """
    Helper function for converting bbox to YOLO format in worker process.
    
    Correctly handles segments that extend beyond the frame by calculating
    only the visible intersection.
    """
    # Calculate the intersection of the bbox with the image frame
    # Original bbox bounds
    x1 = x
    y1 = y
    x2 = x + width
    y2 = y + height
    
    # Clip to image boundaries
    x1_clipped = max(0, x1)
    y1_clipped = max(0, y1)
    x2_clipped = min(img_width, x2)
    y2_clipped = min(img_height, y2)
    
    # Calculate actual visible width and height
    # Ensure non-negative (if bbox is completely outside, this will be 0)
    actual_width = max(0, x2_clipped - x1_clipped)
    actual_height = max(0, y2_clipped - y1_clipped)
    
    # Convert to YOLO format (normalized center coordinates and dimensions)
    # Handle edge case where bbox has zero dimensions
    if actual_width > 0 and actual_height > 0:
        x_center = (x1_clipped + actual_width / 2) / img_width
        y_center = (y1_clipped + actual_height / 2) / img_height
        norm_width = actual_width / img_width
        norm_height = actual_height / img_height
    else:
        # Return zero-size bbox (will be filtered out later)
        x_center = 0.0
        y_center = 0.0
        norm_width = 0.0
        norm_height = 0.0
    
    return (x_center, y_center, norm_width, norm_height)


def main():
    """Example usage"""
    
    # Configuration
    config = {
        'images_dir': '/home/yourusername/SemiF-SyntheticPipeline/data/all_bbot_backgrounds',           # Directory with source images
        # 'labels_dir': '/home/psa_images/temp_data/temp_detection_model/data/train/labels',           # Directory with YOLO .txt files
        'labels_dir': None,
        'segments_dir': '/home/yourusername/AgIR-CVToolkit/outputs/runs/semif_det_synth_cutouts/001/cutouts',       # Directory with RGBA plant cutouts
        'output_images_dir': '/home/yourusername/AgIR-CVToolkit/outputs/runs/semif_det_synth_cutouts/semif_det_synth_cutouts/train/images',  # Where to save augmented images
        'output_labels_dir': '/home/yourusername/AgIR-CVToolkit/outputs/runs/semif_det_synth_cutouts/semif_det_synth_cutouts/train/labels',  # Where to save updated labels
        'plant_class_id': 0,                # YOLO class ID for plants
        'num_segment_range': (3, 8),        # Number of segments to add per image
        'cutoff_range': (0.1, 0.8),         # Random cutoff range (each segment picks randomly)
        'scale_range': (0.2, 1.0),          # Random scale range
        'rotation_range': (-180, 180),      # Random rotation range (degrees)
        'n_workers': 12,                    # Number of workers (None=auto, 1=single-threaded)
        'max_retries': 10,                  # Max attempts to find non-overlapping position per segment
        'overlap_threshold': 0.3            # Maximum IoU overlap allowed with existing bboxes (0.0-1.0)
    }
    
    # Create generator
    generator = SyntheticDataGenerator(
        images_dir=config['images_dir'],
        labels_dir=config['labels_dir'],
        segments_dir=config['segments_dir'],
        output_images_dir=config['output_images_dir'],
        output_labels_dir=config['output_labels_dir'],
        plant_class_id=config['plant_class_id'], 
        random_n_sample=200,
        sample_w_replacement=True
    )
    
    # Process all images
    generator.process_dataset(
        num_segment_range=config['num_segment_range'],
        cutoff_range=config['cutoff_range'],
        scale_range=config['scale_range'],
        rotation_range=config['rotation_range'],
        n_workers=config['n_workers'],
        max_retries=config['max_retries'],
        overlap_threshold=config['overlap_threshold']
    )


if __name__ == '__main__':
    main()