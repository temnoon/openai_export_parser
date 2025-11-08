#!/bin/bash
# Rename all .unknown files to .txt in output directories

# Counter for renamed files
count=0

# Find all .unknown files and rename them
find ~/openai-export-parser/output_* -name "*.unknown" -type f 2>/dev/null | while read -r file; do
    # Get the new filename by replacing .unknown with .txt
    newfile="${file%.unknown}.txt"

    # Rename the file
    mv "$file" "$newfile"

    # Increment counter
    ((count++))

    # Print progress every 100 files
    if ((count % 100 == 0)); then
        echo "Renamed $count files..."
    fi
done

echo "✓ Finished renaming all .unknown files to .txt"
echo "Total files renamed: $count"
