#!/usr/bin/env bash
subname="viz_helpers"
image_id="MD_1690814343"
use_original_mask=false   # set to "false" to run full_image infer-seg
brightness=1.0

agir-cv query --db semif \
    -o project.name="$image_id" \
    -o project.subname=$subname \
    --filters "image_id=$image_id" \
    --out csv


# Only run full_image infer-seg when use_original_mask is false
if [ "$use_original_mask" = "false" ]; then
    agir-cv infer-seg \
        -o project.name="$image_id" \
        -o project.subname=$subname \
        -o seg_inference.source.image_mode=full_image \
        -o seg_inference.source.type=query_result \
        -o seg_inference.output.save_images=false \
        -o seg_inference.output.save_masks=true \
        -o seg_inference.output.save_cutouts=false \
        -o seg_inference.output.cutout_use_rgba=false \
        -o seg_inference.output.save_colorized_masks=true \
        -o seg_inference.output.colorize_brightness=$brightness \
        -o seg_inference.output.save_viz=false
fi

# always run the cutout infer
agir-cv infer-seg \
    -o project.name="$image_id" \
    -o project.subname=$subname \
    -o seg_inference.source.image_mode=cutout \
    -o seg_inference.source.type=query_result \
    -o seg_inference.output.save_images=false \
    -o seg_inference.output.save_masks=false \
    -o seg_inference.output.save_cutouts=true \
    -o seg_inference.output.cutout_use_rgba=true \
    -o seg_inference.output.save_colorized_masks=false \
    -o seg_inference.output.save_viz=false

# Call python and pass --use-original-mask only when requested
py_cmd=(python extract_visuals.py \
    --csv "outputs/runs/$image_id/$subname/query/query.csv" \
    --outdir "outputs/runs/$image_id/$subname/" \
    --brightness $brightness \
    --line-width 18)

if [ "$use_original_mask" = "true" ]; then
    py_cmd+=(--use-original-mask)
fi

"${py_cmd[@]}"