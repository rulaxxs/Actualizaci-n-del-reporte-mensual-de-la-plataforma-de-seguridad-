args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 4L) {
  stop("Uso: Rscript renderizar_reporte_integrado.R plantilla.Rmd tabla.csv corte-AAAA-MM-DD salida.html")
}
if (!requireNamespace("rmarkdown", quietly = TRUE)) {
  stop("Falta instalar el paquete R 'rmarkdown'.")
}

plantilla <- normalizePath(args[[1]], mustWork = TRUE)
tabla <- normalizePath(args[[2]], mustWork = TRUE)
corte <- args[[3]]
salida <- normalizePath(dirname(args[[4]]), mustWork = TRUE)
if (is.na(as.Date(corte))) {
  stop("Corte inválido.")
}

rmarkdown::render(
  input = plantilla,
  output_file = basename(args[[4]]),
  output_dir = salida,
  params = list(tabla_inhumacion_csv = tabla,
                corte_inhumacion = corte),
  envir = new.env(parent = globalenv()),
  quiet = FALSE
)
