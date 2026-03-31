# CSV_Image-Combiner
A tool that can be used to generate multiple copies of an image using rows data from a CSV file.

------------------- A Detailed Example Of How To Use The Tool: -------------------
-

Let's say you want to generate a number of certificates, using one certificate image with no name written in it:
\
\
1- Select a CSV file that contains at least peoples names, could contain grades too.
\
\
2- Select the background image (the empty certificate background).
\
\
3- Spawn rectangles, assign a column to each rectangle, in this case - assign one rectangle to "person name" column header, and another rectangle to "grade/score".
\
\
3.1- Move the rectangles to where you want the person name and the grade/score to be.
\
\
3.2- Press Preview to print an example of how it's going to look. It's going to print the first row data as a preview. (first row that's after the column headers row!)
\
\
3.3- You can insert any font file you would want to use, also change font color and size. Note that the row data will be written at the center of each rectangle depends on which column they represent, if font size is greater than the rectangle dimensions it will be reduced to match the rectangle width and height. You can change each rectangle width and height too to control the maximum font size.
\
\
3.4- You can remove rectangles as you want, can also spawn number of rectangles up to the number of columns detected from the CSV file.
\
\
4- If you like what you see, press the blue generate button and select where you want the final output to be, note that it's going to generate a certificate image for and with every row detected from the CSV file. (up to the amount of rows detected, a file for every row.)
\
\
4.1- The final output files are going to be named 1, 2, 3..., You can add a prefix to each file name if you'd like too.
\
\
4.2- It's going to add "x" to the filenames of images that had missing row data. (for example: not fully complete certificates because they're missing person names, or grades etc.)
\
\
Bonus: This tool was made for a specific job, I tried to make it as universal as possible, but the tool contains extra options (like split output, convert score..) these are meant to be used for specific reasons for the job it was meant for, I can implement a way to make these useful for you too if you want.

I made 60% of this tool as a practice while learning Python, then I used AI to help with complex stuff.
-
