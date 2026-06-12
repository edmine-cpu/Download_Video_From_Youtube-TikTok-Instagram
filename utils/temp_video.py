from pathlib import Path



class TempVideo:
	def __init__(self, path):
		self.path = Path(path)


	async def __aenter__(self):
		return self.path		
	

	def __aexit__(self, exc_type, exc, tb):
		if self.path.exists():
			self.path.unlink()