args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 5L) {
  stop("Uso: Rscript renderizar_reporte_integrado.R plantilla.Rmd tabla.csv corte-AAAA-MM-DD excel.xlsx salida.html")
}
if (!requireNamespace("rmarkdown", quietly = TRUE)) {
  stop("Falta instalar el paquete R 'rmarkdown'.")
}

plantilla <- normalizePath(args[[1]], mustWork = TRUE)
tabla <- normalizePath(args[[2]], mustWork = TRUE)
corte <- args[[3]]
excel <- basename(args[[4]])
salida <- normalizePath(dirname(args[[5]]), mustWork = TRUE)
if (is.na(as.Date(corte)) || !grepl("^[A-Za-z0-9._-]+\\.xlsx$", excel)) {
  stop("Corte o nombre de Excel inválido.")
}

rmarkdown::render(
  input = plantilla,
  output_file = basename(args[[5]]),
  output_dir = salida,
  params = list(tabla_inhumacion_csv = tabla,
                corte_inhumacion = corte,
                excel_descarga = excel),
  envir = new.env(parent = globalenv()),
  quiet = FALSE
)
