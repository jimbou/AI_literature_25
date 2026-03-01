#!/bin/bash

# python pipeline_pl.py   --inputs /home/jim/AI_papers/PLDI/pldi.json   --out_raw_jsonl /home/jim/AI_papers/PLDI/raw_batches_pldi.j
# sonl   --model deepseek-reasoner   --sleep_s 0.5   --max_batches 0   --extract_out_json 
# /home/jim/AI_papers/PLDI/extracted_results_pldi.json   --extract_out_csv /home/jim/AI
# _papers/PLDI/extracted_results_pldi.csv

# python pipeline_pl.py   --inputs /home/jim/AI_papers/POPL/popl.json   --out_raw_jsonl /home/jim/AI_papers/POPL/raw_batches_popl.j
# sonl   --model deepseek-reasoner   --sleep_s 0.5   --max_batches 0   --extract_out_json 
# /home/jim/AI_papers/POPL/extracted_results_popl.json   --extract_out_csv /home/jim/AI
# _papers/POPL/extracted_results_popl.csv

# python pipeline_pl.py   --inputs /home/jim/AI_papers/OOPSLA/oopsla.json   --out_raw_jsonl /home/jim/AI_papers/OOPSLA/raw_batches_oopsla.j
# sonl   --model deepseek-reasoner   --sleep_s 0.5   --max_batches 0   --extract_out_json 
# /home/jim/AI_papers/OOPSLA/extracted_results_oopsla.json   --extract_out_csv /home/jim/AI
# _papers/OOPSLA/extracted_results_oopsla.csv

# python pipeline.py   --inputs /home/jim/AI_papers/NEURIPS/neurips2025_cleaned.json   --out_raw_jsonl /home/jim/AI_papers/NEURIPS/raw_batches_neurips.j
# sonl   --model deepseek-reasoner   --sleep_s 0.5   --max_batches 0   --extract_out_json 
# /home/jim/AI_papers/NEURIPS/extracted_results_neurips.json   --extract_out_csv /home/jim/AI
# _papers/NEURIPS/extracted_results_neurips.csv

# python pipeline.py   --inputs /home/jim/AI_papers/ICLR/iclr2025_cleaned.json   --out_raw_jsonl /home/jim/AI_papers/ICLR/raw_batches_iclr.j
# sonl   --model deepseek-reasoner   --sleep_s 0.5   --max_batches 0   --extract_out_json 
# /home/jim/AI_papers/ICLR/extracted_results_iclr.json   --extract_out_csv /home/jim/AI
# _papers/ICLR/extracted_results_iclr.csv

# python pipeline.py   --inputs /home/jim/AI_papers/AAAI/aaai2025_cleaned.json   --out_raw_jsonl /home/jim/AI_papers/AAAI/raw_batches_aaai.j
# sonl   --model deepseek-reasoner   --sleep_s 0.5   --max_batches 0   --extract_out_json 
# /home/jim/AI_papers/AAAI/extracted_results_aaai.json   --extract_out_csv /home/jim/AI
# _papers/AAAI/extracted_results_aaai.csv


# python pipeline_pl.py \
#   --inputs /home/jim/AI_papers/PLDI/pldi.json \
#   --out_raw_jsonl /home/jim/AI_papers/PLDI/raw_batches_pldi.jsonl \
#   --model deepseek-reasoner \
#   --sleep_s 0.5 \
#   --max_batches 0 \
#   --extract_out_json /home/jim/AI_papers/PLDI/extracted_results_pldi.json \
#   --extract_out_csv /home/jim/AI_papers/PLDI/extracted_results_pldi.csv


# python pipeline_pl.py \
#   --inputs /home/jim/AI_papers/POPL/popl.json \
#   --out_raw_jsonl /home/jim/AI_papers/POPL/raw_batches_popl.jsonl \
#   --model deepseek-reasoner \
#   --sleep_s 0.5 \
#   --max_batches 0 \
#   --extract_out_json /home/jim/AI_papers/POPL/extracted_results_popl.json \
#   --extract_out_csv /home/jim/AI_papers/POPL/extracted_results_popl.csv

# python pipeline_pl.py \
#   --inputs /home/jim/AI_papers/OOPSLA/oopsla.json \
#   --out_raw_jsonl /home/jim/AI_papers/OOPSLA/raw_batches_oopsla.jsonl \
#   --model deepseek-reasoner \
#   --sleep_s 0.5 \
#   --max_batches 0 \
#   --extract_out_json /home/jim/AI_papers/OOPSLA/extracted_results_oopsla.json \
#   --extract_out_csv /home/jim/AI_papers/OOPSLA/extracted_results_oopsla.csv

# python pipeline.py \
#   --inputs /home/jim/AI_papers/NEURIPS/neurips2025_cleaned.json \
#   --out_raw_jsonl /home/jim/AI_papers/NEURIPS/raw_batches_neurips.jsonl \
#   --model deepseek-reasoner \
#   --sleep_s 0.5 \
#   --max_batches 0 \
#   --extract_out_json /home/jim/AI_papers/NEURIPS/extracted_results_neurips.json \
#   --extract_out_csv /home/jim/AI_papers/NEURIPS/extracted_results_neurips.csv

# python pipeline.py \
#   --inputs /home/jim/AI_papers/ICLR/iclr2025_cleaned.json \
#   --out_raw_jsonl /home/jim/AI_papers/ICLR/raw_batches_iclr.jsonl \
#   --model deepseek-reasoner \
#   --sleep_s 0.5 \
#   --max_batches 0 \
#   --extract_out_json /home/jim/AI_papers/ICLR/extracted_results_iclr.json \
#   --extract_out_csv /home/jim/AI_papers/ICLR/extracted_results_iclr.csv

python pipeline.py \
  --inputs /home/jim/AI_papers/AAAI/aaai2025_cleaned.json \
  --out_raw_jsonl /home/jim/AI_papers/AAAI/raw_batches_aaai.jsonl \
  --model deepseek-reasoner \
  --sleep_s 0.5 \
  --max_batches 0 \
  --extract_out_json /home/jim/AI_papers/AAAI/extracted_results_aaai.json \
  --extract_out_csv /home/jim/AI_papers/AAAI/extracted_results_aaai.csv
