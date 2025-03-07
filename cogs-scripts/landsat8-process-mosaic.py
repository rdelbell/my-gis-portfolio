#!/usr/bin/env python3
"""
Automating mosaicking using PCI Geomatica and Python
Author: R Del Bello
Original Date: 02-2020
Updated: 03-2025
Description: Processes raw Landsat 8 imagery through haze removal, atmospheric correction,
and mosaicking in an automated workflow.
"""

from pci.hazerem import hazerem
from pci.atcor import atcor
from pci.automos import automos
from pci.fexport import fexport
from pci.exceptions import PCIException
import sys
import os
import shutil
import fnmatch
from datetime import datetime
import winsound
import ctypes
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LandsatMosaicProcessor:
    """Class to handle Landsat 8 imagery processing and mosaicking"""
    
    def __init__(self, working_dir: str = r'd:\delbello_mosaic'):
        self.working_dir = Path(working_dir)
        self.haze_out = self.working_dir / 'hazerem'
        self.atcor_out = self.working_dir / 'atcor'
        self.mosaic_out = self.working_dir / 'mosaic'
        self.shp_out = self.mosaic_out / 'shp'
        
    def confirm_execution(self) -> bool:
        """Prompt user for confirmation before proceeding"""
        logger.warning("This script will overwrite files in the working directory. Please backup before proceeding")
        return input("Continue? (y/n): ").lower().strip().startswith('y')

    def setup_directories(self) -> None:
        """Initialize and clear working directories"""
        logger.info("=" * 70)
        logger.info("STEP 1: Working directories and path initialization")
        logger.info("=" * 70)
        
        directories = [self.haze_out, self.atcor_out, self.mosaic_out, self.shp_out]
        for directory in directories:
            if directory.exists():
                logger.info(f"Removing {directory}")
                shutil.rmtree(directory, ignore_errors=True)
            directory.mkdir(parents=True)
            logger.info(f"Created {directory}")

    def scan_input_files(self) -> list:
        """Scan for Landsat 8 MTL files"""
        logger.info("Scanning for Landsat 8 Imagery")
        input_files = [
            Path(root) / file
            for root, _, files in os.walk(self.working_dir)
            for file in fnmatch.filter(files, '*MTL.txt')
        ]
        logger.info(f"{len(input_files)} images found")
        return input_files

    def process_haze_removal(self, input_files: list) -> None:
        """Perform haze removal on input files"""
        logger.info("STEP 2: Haze Removal - This will take a few minutes")
        start_time = datetime.now()
        
        for i, image in enumerate(input_files, 1):
            try:
                output_file = self.haze_out / f"hazerem{i}.pix"
                hazerem(
                    fili=f"{image}-MS",
                    hazecov=[40],
                    filo=str(output_file)
                )
                logger.info(f"Processed haze removal for image {i} of {len(input_files)}")
            except (PCIException, Exception) as e:
                logger.error(f"Haze removal error for {image}: {str(e)}")
                
        logger.info(f"STEP 2 COMPLETED. Time taken: {datetime.now() - start_time}")

    def process_atmospheric_correction(self) -> None:
        """Perform atmospheric correction on haze-removed files"""
        logger.info("=" * 70)
        logger.info("STEP 3: Atmospheric Correction - Please be patient...")
        logger.info("=" * 70)
        start_time = datetime.now()

        haze_files = list(self.haze_out.glob('*.pix'))
        saz_angle = [(90 - 18.00963096), 160.40005952]

        for i, image in enumerate(haze_files, 1):
            try:
                output_file = self.atcor_out / f"atcor{i}.pix"
                atcor(
                    fili=str(image),
                    atmdef="desert",
                    atmcond="winter",
                    cfile=r'D:\mosaic\landsat8_oli_template.cal',
                    outunits="Scaled_Reflectance,10.00",
                    sazangl=saz_angle,
                    meanelev=[400],
                    filo=str(output_file)
                )
                logger.info(f"Processed atmospheric correction for image {i} of {len(haze_files)}")
            except (PCIException, Exception) as e:
                logger.error(f"Atmospheric correction error for {image}: {str(e)}")
                
        logger.info(f"ATCOR COMPLETED. Time taken: {datetime.now() - start_time}")

    def create_mosaic(self) -> None:
        """Create mosaic from corrected images"""
        logger.info("STEP 4: Mosaicking - Please be patient")
        try:
            automos(
                mfile=str(self.atcor_out),
                dbiclist="4,3,2",
                mostype='full',
                filo=str(self.mosaic_out / "mosaic.pix"),
                radiocor='adaptive',
                balmthd='overlay',
                cutmthd='mindiff',
                filvout=str(self.shp_out / "cutlines.shp")
            )
        except (PCIException, Exception) as e:
            logger.error(f"Mosaicking error: {str(e)}")

    def export_to_tif(self) -> None:
        """Export mosaic to TIFF format"""
        try:
            fexport(
                fili=str(self.mosaic_out / "mosaic.pix"),
                filo=str(self.mosaic_out / "mosaic.tif"),
                dbic=[1, 2, 3],
                ftype="TIF"
            )
        except (PCIException, Exception) as e:
            logger.error(f"Export error: {str(e)}")

    def run(self) -> None:
        """Execute the full processing pipeline"""
        if not self.confirm_execution():
            logger.info("Execution cancelled by user")
            sys.exit(1)

        self.setup_directories()
        input_files = self.scan_input_files()
        
        if not input_files:
            logger.error("No Landsat 8 MTL files found")
            sys.exit(1)

        self.process_haze_removal(input_files)
        self.process_atmospheric_correction()
        self.create_mosaic()
        self.export_to_tif()

        # Completion notification
        winsound.MessageBeep()
        ctypes.windll.user32.MessageBoxW(
            0,
            "Success! All Landsat 8 Imagery successfully mosaicked. Don't forget to save your files before executing again",
            "Message",
            1
        )

if __name__ == "__main__":
    processor = LandsatMosaicProcessor()
    processor.run()