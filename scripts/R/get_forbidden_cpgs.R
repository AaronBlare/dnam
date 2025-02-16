rm(list=ls())


if (!requireNamespace("BiocManager", quietly=TRUE))
  install.packages("BiocManager")
BiocManager::install("org.Hs.eg.db")
BiocManager::install("DMRcate")
BiocManager::install("GO.db")
BiocManager::install("geneLenDataBase")
BiocManager::install("ChAMP")
install.packages('xlsx')

library(ChAMP)
library("xlsx")

path <- "C:/YandexDisk/Work/pydnameth/datasets/GPL21145/GSE168739/raw/idat"
chip_type = "EPIC"
setwd(path)

myImport <- champ.import(directory = path,
                         arraytype = chip_type)

beta=myImport$beta
M=NULL
pd=myImport$pd
intensity=NULL
Meth=NULL
UnMeth=NULL
detP=NULL
beadcount=NULL
autoimpute=TRUE
filterDetP=TRUE
ProbeCutoff=0
SampleCutoff=0.1
detPcut=0.01
filterBeads=TRUE
beadCutoff=0.05
filterNoCG = TRUE
filterSNPs = TRUE
population = NULL
filterMultiHit = TRUE
filterXY = TRUE
fixOutlier = TRUE
arraytype = chip_type

Objects <- list("beta"=beta,
                "M"=M,
                "intensity"=intensity,
                "Meth"=Meth,
                "UnMeth"=UnMeth)
Objects <- Objects[which(lapply(Objects,FUN=is.null)==FALSE)]

Accessory <- list("detP"=detP,
                  "beadcount"=beadcount)

FilterOption <- list("filterDetP"=filterDetP,
                     "autoimpute"=autoimpute,
                     "filterBeads"=filterBeads,
                     "filterMultiHit"=filterMultiHit,
                     "filterSNPs"=filterSNPs,
                     "filterNoCG"=filterNoCG,
                     "filterXY"=filterXY)

message("\n  Filtering NoCG Start")
RemainProbe <- substr(rownames(Objects[[1]]),1,2) == "cg"
ExcludeProbe <- substr(rownames(Objects[[1]]),1,2) != "cg"
ExcludeCpGs = rownames(Objects[[1]])[ExcludeProbe]
write.xlsx(ExcludeCpGs, "NoCG.xlsx", sheetName = "Sheet1", col.names = FALSE, row.names = FALSE, append = FALSE)

message("\n  Filtering SNPs Start")
if(arraytype=="450K")
{
  if(is.null(population))
  {
    message("    Using general 450K SNP list for filtering.")
    data(hm450.manifest.hg19)
    maskname <- rownames(hm450.manifest.hg19)[which(hm450.manifest.hg19$MASK_general==TRUE)]
  }else if(!population %in% c("AFR","EAS","EUR","SAS","AMR","GWD","YRI","TSI",
                              "IBS","CHS","PUR","JPT","GIH","CHB","STU","ITU",
                              "LWK","KHV","FIN","ESN","CEU","PJL","ACB","CLM",
                              "CDX","GBR","BEB","PEL","MSL","MXL","ASW"))
  {
    message("    Seems your population name is wrong. Using general 450K SNP list for filtering.")
    data(hm450.manifest.hg19)
    maskname <- rownames(hm450.manifest.hg19)[which(hm450.manifest.hg19$MASK_general==TRUE)]
  }else
  {
    message("    Using ",population," specific 450K SNP list for filtering.")
    data(hm450.manifest.pop.hg19)
    maskname <- rownames(hm450.manifest.pop.hg19)[which(hm450.manifest.pop.hg19[,paste("MASK_general_",population,sep="")]==TRUE)]
  }
}else
{
  if(is.null(population))
  {
    message("    Using general EPIC SNP list for filtering.")
    data(EPIC.manifest.hg19)
    maskname <- rownames(EPIC.manifest.hg19)[which(EPIC.manifest.hg19$MASK_general==TRUE)]
  }else if(!population %in% c("AFR","EAS","EUR","SAS","AMR","GWD","YRI","TSI",
                              "IBS","CHS","PUR","JPT","GIH","CHB","STU","ITU",
                              "LWK","KHV","FIN","ESN","CEU","PJL","ACB","CLM",
                              "CDX","GBR","BEB","PEL","MSL","MXL","ASW"))
  {
    message("    Seems your population name is wrong. Using general EPIC SNP list for filtering.")
    data(EPIC.manifest.hg19)
    maskname <- rownames(EPIC.manifest.hg19)[which(EPIC.manifest.hg19$MASK_general==TRUE)]
  }else
  {
    message("    Using ",population," specific EPIC SNP list for filtering.")
    data(EPIC.manifest.pop.hg19)
    maskname <- rownames(EPIC.manifest.pop.hg19)[which(EPIC.manifest.pop.hg19[,paste("MASK_general_",population,sep="")]==TRUE)]
  }
}
ExcludeProbe <- rownames(Objects[[1]]) %in% maskname
ExcludeCpGs = rownames(Objects[[1]])[ExcludeProbe]
write.xlsx(ExcludeCpGs, "SNP.xlsx", sheetName = "Sheet1", col.names = FALSE, row.names = FALSE, append = FALSE)

message("\n  Filtering MultiHit Start")
data(multi.hit)
ExcludeProbe <- rownames(Objects[[1]]) %in% multi.hit$TargetID
ExcludeCpGs = rownames(Objects[[1]])[ExcludeProbe]
write.xlsx(ExcludeCpGs, "MultiHit.xlsx", sheetName = "Sheet1", col.names = FALSE, row.names = FALSE, append = FALSE)

message("\n  Filtering XY Start")
if(arraytype=="EPIC") data(probe.features.epic) else data(probe.features)
ExcludeProbe <- !rownames(Objects[[1]]) %in% (rownames(probe.features)[!probe.features$CHR %in% c("X","Y")])
ExcludeCpGs = rownames(Objects[[1]])[ExcludeProbe]
write.xlsx(ExcludeCpGs, "XY.xlsx", sheetName = "Sheet1", col.names = FALSE, row.names = FALSE, append = FALSE)

