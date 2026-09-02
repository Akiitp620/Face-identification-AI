"""
Responsible ONLY for face processing.
"""
from PIL import Image
import torch
# pyrefly: ignore [missing-import]
from facenet_pytorch import MTCNN, InceptionResnetV1

class FaceEngine:
    def __init__(self):
        # Use MPS (Apple Silicon) if available, else CPU (CUDA usually not on Mac)
        if torch.backends.mps.is_available():
            self.device = torch.device('mps')
        elif torch.cuda.is_available():
            self.device = torch.device('cuda')
        else:
            self.device = torch.device('cpu')
            
        self.mtcnn = MTCNN(keep_all=True, device=self.device)
        self.resnet = InceptionResnetV1(pretrained='vggface2').eval().to(self.device)

    def process_face(self, image: Image.Image):
        """
        Detects a single face in an image and returns its embedding.
        Handles no-face and multiple-face scenarios.
        """
        if image.mode != "RGB":
            image = image.convert("RGB")
            
        faces, probs = self.mtcnn(image, return_prob=True)
        
        if faces is None or len(faces) == 0:
            raise ValueError("No face detected in the image.")
            
        if len(faces) > 1:
            raise ValueError(f"Multiple faces ({len(faces)}) detected. Please provide an image with a single face.")
            
        face_tensor = faces[0].unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            embedding = self.resnet(face_tensor).squeeze(0).cpu().numpy()
            
        return embedding
