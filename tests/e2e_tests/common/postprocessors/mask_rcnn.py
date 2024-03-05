# Copyright (C) 2018-2024 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

"""Mask RCNN postprocessor"""
import logging as log
import sys

import cv2
import numpy as np

from .provider import ClassProvider


class ParseMaskRCNN(ClassProvider):
    """Semantic segmentation parser
    returns new "score" layer, combined from "tf_detections" and "detection_masks".
    For each detected picture it provides matrix of (num of classes + 1, h, w) shape.
    Each submatrix matrix[i] of image size contains probability for each pixel to be classified as i class."""
    __action_name__ = "parse_mask_rcnn_tf"
    log.basicConfig(
        format="[ %(levelname)s ] %(message)s",
        level=log.INFO,
        stream=sys.stdout)

    def __init__(self, config):
        self.target_layers = config.get("target_layers", None)
        self.h = config.get("h")
        self.w = config.get("w")
        self.num_classes = config.get("num_classes")

    def unmold_mask(self, mask: np.ndarray, bbox: list):
        """Converts a mask generated by Mask RCNN to a format similar
        to its original shape.
        mask: [height, width] of type float. A small, typically 28x28 mask.
        bbox: [y1, x1, y2, x2]. The box to fit the mask in.
        Returns a binary mask with the same size as the original image.
        """
        y1, x1, y2, x2 = bbox
        mask = cv2.resize(mask, (x2 - x1, y2 - y1))
        # Put the mask in the right location.
        full_mask = np.zeros((self.w, self.h))
        full_mask[y1:y2, x1:x2] = mask
        return full_mask

    def apply(self, data):
        log.info("Applying {} postprocessor...".format(self.__action_name__))
        """Parse Mask RCNN data."""
        predictions = {'score': []}
        do_data = data["tf_detections"]
        masks = np.zeros(shape=(self.num_classes+1, self.h, self.w))
        masks_data = data["detection_masks"]
        for batch in range(len(do_data)):
            for cur_bounding_box in range(len(do_data[batch])):
                label = int(do_data[batch][cur_bounding_box]['class']) - 1
                x1 = int(min(max(0, do_data[batch][cur_bounding_box]['xmin'] * self.w), self.w))
                y1 = int(min(max(0, do_data[batch][cur_bounding_box]['ymin'] * self.h), self.h))
                x2 = int(min(max(0, do_data[batch][cur_bounding_box]['xmax'] * self.w), self.w))
                y2 = int(min(max(0, do_data[batch][cur_bounding_box]['ymax'] * self.h), self.h))
                num_detected_masks_per_image = int(masks_data.shape[0]/len(do_data))
                current_mask_index = batch * num_detected_masks_per_image + cur_bounding_box
                # Shape of TF masks output blob is 3, IE - 4
                mask = masks_data[current_mask_index][label] if len(masks_data.shape) > 3 else masks_data[current_mask_index]
                mask = self.unmold_mask(mask, [y1, x1, y2, x2])
                masks[label] = mask
        predictions['score'].append(np.array(masks))
        for layer in data.keys():
            if layer not in ["tf_detections", "detection_masks"]:
                predictions[layer] = data[layer]
        return predictions
