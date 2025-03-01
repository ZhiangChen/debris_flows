import matplotlib.pyplot as plt
import matplotlib.image as mpimg

# Define image file paths (replace these with actual paths)
image_paths = [
    "auburn.png",
    "bailey.png",
    "sierramadredam.png",
    "sunnyside.png"
]

# Create the main figure
fig, axs = plt.subplots(2, 2, figsize=(12, 10))

# Titles for each subfigure
titles = ["(a) Auburn", "(b) Bailey", "(c) Sierra Mandre Dam", "(d) Sunnyside"]

# Loop through each subplot and add the corresponding image
for ax, img_path, title in zip(axs.flatten(), image_paths, titles):
    img = mpimg.imread(img_path)  # Read image
    ax.imshow(img)  # Display image
    ax.set_title(title, fontsize=14)  # Set title
    ax.axis("off")  # Hide axis

# Adjust layout
plt.tight_layout()
plt.savefig("composed_figure.png", dpi=300)  # Save the figure
#plt.show()

# compose two figures
fig, axs = plt.subplots(1, 2, figsize=(12, 5))
img1 = mpimg.imread("dem.png")
img2 = mpimg.imread("dsm.png")
axs[0].imshow(img1)
axs[0].set_title("(a) DEM", fontsize=14)
axs[0].axis("off")
axs[1].imshow(img2)
axs[1].set_title("(b) DSM", fontsize=14)
axs[1].axis("off")

plt.tight_layout()
plt.savefig("composed_figure2.png", dpi=300)