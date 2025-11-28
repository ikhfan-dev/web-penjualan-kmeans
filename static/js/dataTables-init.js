/**
 * Fungsi untuk menginisialisasi DataTable dengan opsi yang umum digunakan.
 * @param {string} tableId - ID dari tabel HTML yang akan diubah menjadi DataTable.
 * @param {object} options - Opsi tambahan untuk menimpa opsi default.
 */
function initializeDataTable(tableId, options = {}) {
    // Opsi default
    const defaultOptions = {
        responsive: true,
        pageLength: 10,
        lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, "Semua"]],
        language: {
            url: '/static/i18n/id.json',
            "sSearch": "Cari:",
            "sLengthMenu": "Tampilkan _MENU_ entri",
            "sInfo": "Menampilkan _START_ hingga _END_ dari _TOTAL_ entri",
            "sInfoEmpty": "Tidak ada data yang tersedia dalam tabel",
            "sInfoFiltered": "(disaring dari _MAX_ total entri)",
            "sZeroRecords": "Tidak ada data yang cocok dengan pencarian",
            "oPaginate": {
                "sFirst": "Pertama",
                "sLast": "Terakhir",
                "sNext": "Selanjutnya",
                "sPrevious": "Sebelumnya"
            },
            "oAria": {
                "sSortAscending": ": aktifkan untuk mengurutkan kolom ini",
                "sSortDescending": ": aktifkan untuk mengurutkan kolom ini"
            }
        },
        // Konfigurasi DOM untuk menempatkan elemen (search, pagination, dll)
        dom: "<'row'<'t'<'col-sm-12 col-md-6'l><'row'<'col-sm-12 col-md-6'f>'p>t<'col-sm-12 col-md-6'f>>" +
                "<'row'<'col-sm-12 col-md-6'l><'row'<'col-sm-12 col-md-6'f><'row'<'col-sm-12 col-md-6'i><'row'<'col-sm-12 col-md-6'f>>" +
                "<'table-responsive'tr>" +
                "</table>" +
                "</div>" +
                "</div>" +
                "</div>" +
                "</div>" +
                "</div>" +
                "</div>" +
                "</div>" +
                "</div>",
        // Konfigurasi tombol export
        buttons: [
            {
                extend: 'collection',
                text: 'Export',
                className: 'btn btn-secondary btn-sm',
                buttons: [
                    { extend: 'copy', className: 'btn btn-light' },
                    { extend: 'csv', className: 'btn btn-light' },
                    { extend: 'excel', className: 'btn btn-light' },
                    { extend: 'pdf', className: 'btn btn-light' }
                ]
            }
        ]
    };

    // Gabungkan opsi default dengan opsi kustom
    const finalOptions = { ...defaultOptions, ...options };

    // Inisialisasi DataTable
    $(`#${tableId}`).DataTable(finalOptions);
}