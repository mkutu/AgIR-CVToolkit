
# SemiF - 20 samples per species
# agir-cv query --db semif \
#     -o project.name="semif_det_synth_cutouts" \
#     -o project.subname="001" \
#     --filters "estimated_bbox_area_cm2>100" \
#     --filters "estimated_bbox_area_cm2<800" \
#     --sample "stratified:by=category_common_name,per_group=5" \
#     --out csv

# agir-cv query --db semif \
#     -o project.name="det_results" \
#     -o project.subname="001" \
#     --sample "stratified:by=category_common_name|estimated_area_bin,per_group=5"

    # --sample "random:n=200" \
    # --filters "category_common_name=maize" \
    # --filters "estimated_bbox_area_cm2>1000" \

# agir-cv infer-seg \
#     -o project.name=semif_det_synth_cutouts \
#     -o project.subname="001" \
#     -o seg_inference.source.image_mode=cutout \
#     -o seg_inference.source.type=query_result \
#     -o seg_inference.output.save_images=false \
#     -o seg_inference.output.save_masks=false \
#     -o seg_inference.output.save_cutouts=true \
#     -o seg_inference.output.cutout_use_rgba=true \
#     -o seg_inference.output.save_colorized_masks=false \
#     -o seg_inference.output.save_viz=false

# python synthetic_data_gen.py

agir-cv infer-det \
    -o project.name="det_results" \
    -o project.subname="001" \
    -o det_inference.post_fusion_nms.enabled=false
mv outputs/runs/det_results/001/plots outputs/runs/det_results/001/plots_without_pfnms_v2
agir-cv infer-det \
    -o project.name="det_results" \
    -o project.subname="001" \
    -o det_inference.post_fusion_nms.enabled=true
mv outputs/runs/det_results/001/plots outputs/runs/det_results/001/plots_with_pfnms_v2
